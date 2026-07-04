use std::sync::Mutex;
use tauri::Manager;
use tauri_plugin_shell::ShellExt;

struct BackendState {
    port: Mutex<String>,
}

#[tauri::command]
fn get_backend_port(state: tauri::State<'_, BackendState>) -> String {
    let port = state.port.lock().unwrap();
    port.clone()
}

#[tauri::command]
fn save_file_to_path(path: String, data: Vec<u8>) -> Result<(), String> {
    use std::fs::File;
    use std::io::Write;
    let mut file = File::create(&path).map_err(|e| e.to_string())?;
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
    fs::copy(&src_path, &dest_path).map_err(|e| e.to_string())?;
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
                port: Mutex::new("8081".to_string()),
            });

            // "mmtools-backend" refers to the sidecar defined in tauri.conf.json
            let (mut rx, _child) = shell
                .sidecar("mmtools-backend")
                .expect("failed to setup sidecar")
                .env("STORAGE_BASE_DIR", &app_data_str)
                .env("GRPC_AUTH_DISABLED", "true")
                .env("DATA_ACCESS_TOKEN", "mmtools-default-secret-2024")
                .spawn()
                .expect("failed to spawn sidecar");

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

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_backend_port,
            save_file_to_path,
            copy_file_from_storage
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
