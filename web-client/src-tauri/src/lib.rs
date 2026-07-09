use std::sync::Mutex;
use tauri::Manager;
use tauri_plugin_shell::ShellExt;

struct BackendState {
    port: Mutex<String>,
    child: Mutex<Option<tauri_plugin_shell::process::CommandChild>>,
}

#[tauri::command]
fn get_backend_port(state: tauri::State<'_, BackendState>) -> String {
    let port = state.port.lock().unwrap();
    port.clone()
}

#[tauri::command]
fn save_file_to_path(path: String, data_base64: String) -> Result<(), String> {
    use std::fs::File;
    use std::io::Write;
    use std::path::Path;
    use base64::{Engine as _, engine::general_purpose};

    let p = Path::new(&path);
    if !p.is_absolute() {
        return Err("Path must be absolute".into());
    }
    let name = p.file_name().and_then(|n| n.to_str()).unwrap_or("");
    let name_lower = name.to_lowercase();
    if name_lower == ".zshrc"
        || name_lower == ".bashrc"
        || name_lower == ".bash_profile"
        || name_lower == ".profile"
        || name_lower == "authorized_keys"
    {
        return Err("Forbidden file name".into());
    }

    let path_str = path.replace("\\", "/");
    if path_str.contains("/.ssh/")
        || path_str.contains("/.gnupg/")
        || path_str.contains("/etc/")
        || path_str.contains("/Windows/")
        || path_str.contains("/System/")
    {
        return Err("Forbidden destination directory".into());
    }

    let data = general_purpose::STANDARD.decode(&data_base64).map_err(|e| e.to_string())?;
    let mut file = File::create(p).map_err(|e| e.to_string())?;
    file.write_all(&data).map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
fn copy_file_from_storage(
    app: tauri::AppHandle,
    relative_path: String,
    dest_path: String,
) -> Result<(), String> {
    use std::fs;
    let app_data_dir = app.path().app_data_dir().map_err(|e| e.to_string())?;
    let src_path = app_data_dir.join(&relative_path);
    if !src_path.exists() {
        return Err(format!("Source file does not exist: {:?}", src_path));
    }

    // Canonicalize paths to resolve relative segments and symlinks securely
    let src_canonical = src_path
        .canonicalize()
        .map_err(|e| format!("Invalid source path: {}", e))?;
    let app_data_canonical = app_data_dir
        .canonicalize()
        .map_err(|e| format!("Invalid app data directory: {}", e))?;

    if !src_canonical.starts_with(&app_data_canonical) {
        return Err("Access denied: path traversal detected".into());
    }

    fs::copy(&src_canonical, &dest_path).map_err(|e| e.to_string())?;
    Ok(())
}


#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(
            tauri_plugin_log::Builder::default()
                .level(log::LevelFilter::Info)
                .timezone_strategy(tauri_plugin_log::TimezoneStrategy::UseLocal)
                .build(),
        )
        .setup(|app| {
            let shell = app.shell();
            let app_data_dir = app
                .path()
                .app_data_dir()
                .expect("failed to get app data dir");
            let app_data_str = app_data_dir.to_string_lossy().to_string();

            app.manage(BackendState {
                port: Mutex::new("".to_string()),
                child: Mutex::new(None),
            });

            let resource_dir = app
                .path()
                .resource_dir()
                .expect("failed to get resource dir");
            let resource_dir_str = resource_dir.to_string_lossy().to_string();

            // Propagate LOG_LEVEL if set, otherwise default to INFO
            let log_level = std::env::var("LOG_LEVEL").unwrap_or_else(|_| "INFO".to_string());

            let (mut rx, child) = shell
                .sidecar("mmtools-backend")
                .expect("failed to setup sidecar")
                .env("STORAGE_BASE_DIR", &app_data_str)
                .env("GRPC_AUTH_DISABLED", "true")
                .env("DATA_ACCESS_TOKEN", "mmtools-default-secret-2024")
                .env("MONITOR_PARENT_PROCESS", "true")
                .env("TAURI_RESOURCE_DIR", &resource_dir_str)
                .env("LOG_LEVEL", &log_level)
                .spawn()
                .expect("failed to spawn sidecar");

            let state = app.state::<BackendState>();
            let mut child_guard = state.child.lock().unwrap();
            *child_guard = Some(child);

            let handle = app.handle().clone();
            // Log sidecar output in background
            tauri::async_runtime::spawn(async move {
                use tauri_plugin_shell::process::CommandEvent;
                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stdout(line) => {
                            let text = String::from_utf8_lossy(&line);
                            log::info!("Sidecar (stdout): {}", text);
                            if text.contains("REST Gateway + Health check server starting on port")
                            {
                                if let Some(port_part) = text.split("port ").nth(1) {
                                    let cleaned_port = port_part.trim().replace(".", "");
                                    if !cleaned_port.is_empty() {
                                        let state = handle.state::<BackendState>();
                                        let mut port = state.port.lock().unwrap();
                                        *port = cleaned_port.clone();
                                        log::info!(
                                            "Tauri captured dynamic backend REST port: {}",
                                            cleaned_port
                                        );
                                    }
                                }
                            }
                        }
                        CommandEvent::Stderr(line) => {
                            let text = String::from_utf8_lossy(&line);
                            log::error!("Sidecar (stderr): {}", text);
                            if text.contains("REST Gateway + Health check server starting on port")
                            {
                                if let Some(port_part) = text.split("port ").nth(1) {
                                    let cleaned_port = port_part.trim().replace(".", "");
                                    if !cleaned_port.is_empty() {
                                        let state = handle.state::<BackendState>();
                                        let mut port = state.port.lock().unwrap();
                                        *port = cleaned_port.clone();
                                        log::info!(
                                            "Tauri captured dynamic backend REST port: {}",
                                            cleaned_port
                                        );
                                    }
                                }
                            }
                        }
                        CommandEvent::Terminated(payload) => {
                            log::info!("Sidecar terminated with status: {:?}", payload.code);
                        }
                        _ => {}
                    }
                }
            });

            // Wait for backend REST server to start and port to become connectable
            log::info!("Waiting for backend REST server to start...");
            let mut ready = false;
            let start_time = std::time::Instant::now();
            let timeout = std::time::Duration::from_secs(45);
            
            while start_time.elapsed() < timeout {
                let current_port = {
                    let state = app.state::<BackendState>();
                    let port_guard = state.port.lock().unwrap();
                    port_guard.clone()
                };
                
                if !current_port.is_empty() {
                    let addr = format!("127.0.0.1:{}", current_port);
                    if let Ok(_stream) = std::net::TcpStream::connect(&addr) {
                        log::info!("Successfully connected to backend REST server at {}", addr);
                        ready = true;
                        break;
                    }
                }
                
                std::thread::sleep(std::time::Duration::from_millis(100));
            }
            
            if !ready {
                log::error!("Backend REST server failed to start within timeout.");
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_backend_port,
            save_file_to_path,
            copy_file_from_storage
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            if let tauri::RunEvent::Exit = event {
                let child = {
                    let state = app_handle.state::<BackendState>();
                    let x = state.child.lock().unwrap().take();
                    x
                };
                if let Some(child) = child {
                    let _ = child.kill();
                    log::info!("Sidecar process terminated successfully.");
                }
            }
        });
}
