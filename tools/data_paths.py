from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent
UESP_DATA_ROOT = REPO_ROOT / "data" / "eso_info"
UESP_CACHE_ROOT = UESP_DATA_ROOT / ".cache"
UESP_IMPORT_LOG_PATH = UESP_DATA_ROOT / "import_log.jsonl"
