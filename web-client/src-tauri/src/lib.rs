use tauri_plugin_shell::ShellExt;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  let child_state = std::sync::Arc::new(std::sync::Mutex::new(None));
  let child_state_clone = child_state.clone();

  tauri::Builder::default()
    .plugin(tauri_plugin_shell::init())
    .plugin(tauri_plugin_log::Builder::default()
      .level(log::LevelFilter::Info)
      .build())
    .setup(move |app| {
      let shell = app.shell();
      // "mmtools-backend" refers to the sidecar defined in tauri.conf.json
      let (mut rx, child) = shell
        .sidecar("mmtools-backend")
        .expect("failed to setup sidecar")
        .env("GRPC_AUTH_DISABLED", "true")
        .env("USE_MOCK_FIRESTORE", "true")
        .env("NEXT_PUBLIC_AUTH_DISABLED", "true")
        .spawn()
        .expect("failed to spawn sidecar");

      *child_state_clone.lock().unwrap() = Some(child);

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
    .build(tauri::generate_context!())
    .expect("error while building tauri application")
    .run(move |_app_handle, event| {
      if let tauri::RunEvent::Exit = event {
        if let Some(child) = child_state.lock().unwrap().take() {
          let _ = child.kill();
        }
      }
    });
}
