import sys
from src.pipeline.build.build_preview import build_preview
from src.utils.status_helper import update_status


def run(args):
    """
    Execute build subcommand: construct interactive HTML book reader preview
    from archived chapter pages.

    Supports --verify flag to run verify-resources checks after a successful build.
    """
    book_slug = args.book
    mode = getattr(args, "mode", "bilingual")
    copy_to_web = getattr(args, "copy_to_web", False)
    verify = getattr(args, "verify", False)

    print(f"\n{'='*60}")
    print(f"  BUILD PREVIEW: BOOK '{book_slug}' MODE '{mode}'")
    if copy_to_web:
        print("  (COPY TO WEB SITE DIRECTORY ENABLED)")
    if verify:
        print("  (POST-BUILD RESOURCE VERIFICATION ENABLED)")
    print(f"{'='*60}\n")

    status_code, result = build_preview(book_slug, mode=mode, copy_to_web=copy_to_web)

    if status_code != 0:
        print(f"Error: {result}")
        update_status(book_slug, phase="build", status_str="failed", error_msg=str(result))
        return status_code

    print("Build Execution Summary:")
    print(f"  - Output location: {result['output_dir']}")
    print(f"  - Total pages compiled: {result['total_pages']}")
    print(f"  - Landing redirect page: {result['first_page']}")
    print("\nPreview build completed successfully!")

    update_status(book_slug, phase="build", status_str="completed",
                  extra_metadata={"total_pages": result["total_pages"],
                                  "first_page": result["first_page"],
                                  "mode": mode,
                                  "copy_to_web": copy_to_web})

    # Run post-build resource verification if --verify is set
    if verify:
        print("\nRunning post-build resource verification...")
        from src.qa.resource_verifier import verify_book_resources

        stages_to_check = ["preview"]
        if copy_to_web:
            stages_to_check.append("web")

        overall_ok = True
        for stg in stages_to_check:
            vc, report = verify_book_resources(book_slug, stage=stg)
            if vc != 0:
                overall_ok = False
                print(f"\n[verify:{stg}] FAILED — {report['total_errors']} error(s):")
                for errs in report["errors"].values():
                    for e in errs:
                        print(f"  ERROR {e}")
            else:
                print(f"[verify:{stg}] PASSED")

        if not overall_ok:
            print("\nBuild succeeded but resource verification FAILED.")
            return 1

        print("\nAll resource checks passed.")

    return 0
