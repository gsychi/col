//! Certificate-only CLI; never falls back to full-board search.
fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.get(1).map(String::as_str) == Some("verify") {
        let result = (|| -> Result<(), String> {
            let path = args.get(2).ok_or("usage: col-cert verify PROOF.json")?;
            if std::path::Path::new(path).is_dir() {
                col_rs::tiling::check_fixture(std::path::Path::new(path))?;
                println!("VERIFIED: original 3x15 fixture, all local edges and opening/family assemblies");
                return Ok(());
            }
            let report: col_rs::tiling::Report =
                serde_json::from_slice(&std::fs::read(path).map_err(|e| e.to_string())?)
                    .map_err(|e| e.to_string())?;
            col_rs::tiling::check_report(&report)?;
            println!(
                "VERIFIED: {}x{} {} (side to move); {} opening cases",
                report.height,
                report.width,
                report.outcome,
                report.openings.len()
            );
            Ok(())
        })();
        if let Err(e) = result {
            eprintln!("INVALID: {e}");
            std::process::exit(1);
        }
    } else {
        let mut solver_args = args;
        solver_args.push("--certificate-only".into());
        col_rs::run(solver_args);
    }
}
