use tauri_plugin_shell::ShellExt;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .plugin(tauri_plugin_shell::init())
    .plugin(tauri_plugin_log::Builder::default()
      .level(log::LevelFilter::Info)
      .build())
    .setup(|app| {
      let shell = app.shell();
      // "mmtools-backend" refers to the sidecar defined in tauri.conf.json
      let (mut rx, _child) = shell
        .sidecar("mmtools-backend")
        .expect("failed to setup sidecar")
        .env("GRPC_AUTH_DISABLED", "true")
        .env("USE_MOCK_FIRESTORE", "true")
        .env("NEXT_PUBLIC_AUTH_DISABLED", "true")
        .spawn()
        .expect("failed to spawn sidecar");

      // Log sidecar output in background
      tauri::async_runtime::spawn(async move {
        use tauri_plugin_shell::process::CommandEvent;
        while let Some(event) = rx.recv().await {
          match event {
            CommandEvent::Stdout(line) => {
              log::info!("Sidecar (stdout): {}", String::from_utf8_lossy(&line));
            }
            CommandEvent::Stderr(line) => {
              log::error!("Sidecar (stderr): {}", String::from_utf8_lossy(&line));
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
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}

