"""
Configuration loader for LeadGen India
Loads from .env file and supports service account JSON file
"""
import os
import json
from pathlib import Path
from typing import Optional

# Try to load python-dotenv if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed. Using environment variables only.")
    print("   Install with: pip install python-dotenv")


def load_service_account_json() -> Optional[str]:
    """
    Load Google Service Account JSON from file or environment variable.
    Priority: GOOGLE_SERVICE_ACCOUNT_JSON env var > service_account.json file
    """
    # First try environment variable (for Render deployment)
    env_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON', '')
    if env_json:
        try:
            # Validate it's proper JSON
            json.loads(env_json)
            return env_json
        except json.JSONDecodeError:
            print("⚠️  GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON")
    
    # Try file path from environment
    file_path = os.environ.get('GOOGLE_SERVICE_ACCOUNT_FILE', 'service_account.json')
    
    # Check if file exists
    if Path(file_path).exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Validate JSON
                json.loads(content)
                print(f"✓ Loaded service account from: {file_path}")
                return content
        except Exception as e:
            print(f"⚠️  Error reading {file_path}: {e}")
    
    return ''


def get_config() -> dict:
    """
    Get configuration from environment variables.
    Returns dict with all required config keys.
    """
    return {
        'serpapi_key': os.environ.get('SERPAPI_KEY', ''),
        'openrouter_key': os.environ.get('OPENROUTER_KEY', ''),
        'hunter_key': os.environ.get('HUNTER_KEY', ''),
        'sheet_id': os.environ.get('SHEET_ID', ''),
        'sheets_service_account_json': load_service_account_json(),
        'min_score': int(os.environ.get('MIN_SCORE', '7')),
        'max_concurrent_scrapes': int(os.environ.get('MAX_CONCURRENT', '5')),
    }


def validate_config(config: dict, require_sheets: bool = True) -> list[str]:
    """
    Validate configuration and return list of missing/invalid keys.
    
    Args:
        config: Config dict from get_config()
        require_sheets: Whether Google Sheets config is required
    
    Returns:
        List of error messages (empty if all valid)
    """
    errors = []
    
    if not config['serpapi_key']:
        errors.append("SERPAPI_KEY is required")
    
    if not config['openrouter_key']:
        errors.append("OPENROUTER_KEY is required for AI scoring")
    
    if require_sheets:
        if not config['sheet_id']:
            errors.append("SHEET_ID is required")
        
        if not config['sheets_service_account_json']:
            errors.append("Google Service Account JSON is required (GOOGLE_SERVICE_ACCOUNT_JSON or service_account.json file)")
    
    return errors


if __name__ == '__main__':
    """Test configuration loading"""
    print("=== Configuration Test ===\n")
    
    config = get_config()
    
    print("Loaded config:")
    print(f"  SERPAPI_KEY: {'✓ Set' if config['serpapi_key'] else '✗ Missing'}")
    print(f"  OPENROUTER_KEY: {'✓ Set' if config['openrouter_key'] else '✗ Missing'}")
    print(f"  HUNTER_KEY: {'✓ Set' if config['hunter_key'] else '✗ Missing (optional)'}")
    print(f"  SHEET_ID: {'✓ Set' if config['sheet_id'] else '✗ Missing'}")
    print(f"  Service Account: {'✓ Set' if config['sheets_service_account_json'] else '✗ Missing'}")
    print(f"  MIN_SCORE: {config['min_score']}")
    print(f"  MAX_CONCURRENT: {config['max_concurrent_scrapes']}")
    
    print("\nValidation:")
    errors = validate_config(config)
    if errors:
        print("  ✗ Errors found:")
        for err in errors:
            print(f"    - {err}")
    else:
        print("  ✓ All required config is valid!")
