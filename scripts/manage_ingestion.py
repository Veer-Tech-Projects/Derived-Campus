import sys
import os
import argparse
import time
import logging

# 1. Setup Paths (To allow importing from 'backend')
CURRENT_SCRIPT_PATH = os.path.abspath(__file__)
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_SCRIPT_PATH))
sys.path.append(os.path.join(PROJECT_ROOT, "backend"))

import app.worker.celery_app

from ingestion.common.services.plugin_factory import PluginFactory
from ingestion.tasks import perform_exam_scan

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("IngestionManager")

class IngestionCLI:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description="Derived Campus Ingestion Manager")
        self.parser.add_argument("--interactive", action="store_true", help="Run in interactive wizard mode")
        subparsers = self.parser.add_subparsers(dest="command", help="Available commands")

        # Command: bootstrap
        parser_bootstrap = subparsers.add_parser("bootstrap", help="Queue historical discovery scans")
        parser_bootstrap.add_argument("exam", nargs="?", type=str, help="Exam slug (e.g., kcet)")
        parser_bootstrap.add_argument("--years", nargs="+", type=int, help="List of years (e.g., 2020 2021)")
        parser_bootstrap.add_argument("--throttle", type=int, default=2, help="Seconds to wait between dispatches")

    def run(self):
        args = self.parser.parse_args()

        # Default to Interactive Mode if no command is provided
        if args.interactive or args.command is None:
            self.run_interactive()
        elif args.command == "bootstrap":
            if not args.exam or not args.years:
                print("❌ Error: Bootstrap command requires 'exam' and '--years' arguments.")
                print("   Use --interactive for a guided experience.")
                return
            self.bootstrap(args.exam, args.years, args.throttle)

    def run_interactive(self):
        print("\n========================================")
        print("   DERIVED CAMPUS INGESTION MANAGER")
        print("========================================")
        
        # 1. Select Exam
        plugins = PluginFactory.list_available_plugins()
        print("\nAvailable Exams:")
        for idx, slug in enumerate(plugins):
            print(f"  [{idx + 1}] {slug.upper()}")
        
        try:
            selection = int(input("\nSelect Exam Number: ")) - 1
            if selection < 0 or selection >= len(plugins):
                print("❌ Invalid selection.")
                return
            exam_slug = plugins[selection]
        except ValueError:
            print("❌ Invalid input.")
            return

        # 2. Select Years
        try:
            plugin_instance = PluginFactory.get_plugin(exam_slug)
            
            # NOTE: We assume get_seed_urls() is a STATIC configuration method.
            # It should not perform network I/O to prevent CLI hanging.
            available_years = sorted(list(plugin_instance.get_seed_urls().keys()))
            
            print(f"\nSupported Years for {exam_slug.upper()}:")
            print(f"  {available_years}")
            
            years_input = input("\nEnter years to bootstrap (comma separated, e.g. 2023, 2024): ")
            selected_years = [int(y.strip()) for y in years_input.split(",") if y.strip()]
            
            # Validate years exist in plugin
            valid_years = [y for y in selected_years if y in available_years]
            if len(valid_years) != len(selected_years):
                print(f"⚠️ Warning: Some years were ignored because they are not supported by the plugin.")
            
            if not valid_years:
                print("❌ No valid years selected.")
                return

        except Exception as e:
            print(f"❌ Error loading plugin configuration: {e}")
            return

        # 3. Confirm & Execute
        print(f"\nReady to dispatch {len(valid_years)} tasks to 'bootstrap_queue'.")
        confirm = input("Proceed? (y/n): ")
        if confirm.lower() == 'y':
            self.bootstrap(exam_slug, valid_years, throttle=2)
        else:
            print("Cancelled.")

    def bootstrap(self, exam: str, years: list, throttle: int):
        print(f"\n🚀 INITIALIZING BOOTSTRAP: {exam.upper()}")
        print(f"   Target Years: {years}")
        print(f"   Queue: 'bootstrap_queue'")
        print("-" * 50)

        dispatched_count = 0
        for year in years:
            print(f"   ... Preparing {year} ... ", end="")
            try:
                # --- EXPLICIT ROUTING (The Safety Guardrail) ---
                task = perform_exam_scan.apply_async(
                    args=[exam, year],
                    queue="bootstrap_queue" 
                )
                print(f"✅ Dispatched! Task ID: {task.id}")
                dispatched_count += 1
            except Exception as e:
                print(f"❌ Failed to dispatch: {e}")

            if throttle > 0:
                time.sleep(throttle)

        print("-" * 50)
        print(f"🎉 DONE. {dispatched_count} tasks sent to the Background Worker.")

if __name__ == "__main__":
    IngestionCLI().run()