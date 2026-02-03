#!/usr/bin/env python3
"""
Data validation utilities.

Required files:
- data_validator.py
- tides.json (validated/initialized by this module)

Dependencies:
- Python 3 (stdlib only)

Details:
- Comprehensive data validation and error handling utilities
- Handles tides.json validation, template creation, graceful degradation, and caching
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

class DataValidator:
    """Validates and manages tides.json data with graceful error handling"""
    
    # Expected structure for tides.json
    TEMPLATE = {
        "goat_rock": {},
        "estuary": {},
        "fort_ross": {},
        "bodega_tides": {},
        "jenner_stage_history": {},
        "data_sources": {
            "goat_rock_updated": None,
            "estuary_updated": None,
            "fort_ross_updated": None,
            "bodega_updated": None,
            "jenner_stage_updated": None,
            "hacienda_stage": None,
            "hacienda_cfs": None,
            "river_mouth_status": None
        },
        "hacienda_stage": "--",
        "hacienda_cfs": "--",
        "jenner_stage": "--",
        "river_mouth_status": "UNKNOWN"
    }
    
    @staticmethod
    def create_template_if_missing(data_file="tides.json"):
        """Create tides.json template if file is missing"""
        if os.path.exists(data_file):
            return True
        
        try:
            Path(data_file).parent.mkdir(parents=True, exist_ok=True)
            with open(data_file, "w") as f:
                json.dump(DataValidator.TEMPLATE, f, indent=4)
            print(f"✓ Created template: {data_file}")
            return True
        except Exception as e:
            print(f"✗ Failed to create template: {e}")
            return False
    
    @staticmethod
    def validate_structure(data):
        """Validate that data has required structure"""
        if not isinstance(data, dict):
            return False, "Data is not a dictionary"
        
        required_keys = ["goat_rock", "estuary", "jenner_stage_history"]
        for key in required_keys:
            if key not in data:
                return False, f"Missing required key: {key}"
            if not isinstance(data[key], dict):
                return False, f"Key '{key}' should be dict, got {type(data[key])}"
        
        return True, "Valid structure"
    
    @staticmethod
    def validate_tide_entry(entry):
        """Validate a single tide entry [label, time, height]"""
        if not isinstance(entry, (list, tuple)) or len(entry) != 3:
            return False
        label, time_str, height_str = entry
        if not isinstance(label, str) or label not in ["Low", "High"]:
            return False
        if not isinstance(time_str, str) or ":" not in time_str:
            return False
        if not isinstance(height_str, str) or "ft" not in height_str:
            return False
        return True
    
    @staticmethod
    def validate_stage_entry(entry):
        """Validate a single stage entry {time, minutes, stage}"""
        if not isinstance(entry, dict):
            return False
        if "minutes" not in entry or "stage" not in entry:
            return False
        try:
            int(entry["minutes"])
            float(entry["stage"])
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_tides_data(data):
        """Validate tides.json content and report issues"""
        issues = []
        
        # Check structure
        valid_structure, msg = DataValidator.validate_structure(data)
        if not valid_structure:
            return issues, msg, False
        
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Check each tide station
        stations = {
            "goat_rock": "Goat Rock",
            "estuary": "Estuary",
            "fort_ross": "Fort Ross",
            "bodega_tides": "Bodega"
        }
        
        for station_key, station_name in stations.items():
            station_data = data.get(station_key, {})
            if not station_data:
                issues.append(f"⚠ {station_name} has no data")
                continue
            
            today_data = station_data.get(today, [])
            if not today_data:
                issues.append(f"⚠ {station_name} missing today's data")
            else:
                invalid_count = sum(1 for e in today_data if not DataValidator.validate_tide_entry(e))
                if invalid_count > 0:
                    issues.append(f"⚠ {station_name} has {invalid_count} invalid entries")
        
        # Check stage data
        stage_data = data.get("jenner_stage_history", {})
        if not stage_data:
            issues.append("⚠ Jenner stage history missing")
        else:
            today_stage = stage_data.get(today, [])
            if not today_stage:
                issues.append("⚠ Jenner stage missing today's data")
            else:
                invalid_stage = sum(1 for e in today_stage if not DataValidator.validate_stage_entry(e))
                if invalid_stage > 0:
                    issues.append(f"⚠ Stage has {invalid_stage} invalid entries")
        
        # Determine overall health
        critical = len(issues) > 3 or any("missing today" in i for i in issues)
        return issues, "Data validated with warnings" if issues else "Data OK", not critical
    
    @staticmethod
    def get_data_age(data):
        """Get age of data in seconds, returns dict with source ages"""
        ages = {}
        now = datetime.now()
        
        sources = [
            ("goat_rock_updated", "Goat Rock"),
            ("estuary_updated", "Estuary"),
            ("jenner_stage_updated", "Stage"),
            ("fort_ross_updated", "Fort Ross"),
            ("bodega_updated", "Bodega")
        ]
        
        data_sources = data.get("data_sources", {})
        
        for key, name in sources:
            timestamp_str = data_sources.get(key)
            if timestamp_str:
                try:
                    ts = datetime.fromisoformat(timestamp_str)
                    age_seconds = (now - ts).total_seconds()
                    age_minutes = int(age_seconds / 60)
                    ages[name] = {
                        "age_seconds": age_seconds,
                        "age_minutes": age_minutes,
                        "timestamp": timestamp_str,
                        "stale": age_minutes > 120  # Stale if > 2 hours
                    }
                except:
                    ages[name] = {
                        "age_seconds": None,
                        "age_minutes": None,
                        "timestamp": timestamp_str,
                        "stale": True
                    }
            else:
                ages[name] = {
                    "age_seconds": None,
                    "age_minutes": None,
                    "timestamp": None,
                    "stale": True
                }
        
        return ages
    
    @staticmethod
    def get_available_data(data):
        """Return what data is available, what's missing"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        available = {
            "goat_rock": bool(data.get("goat_rock", {}).get(today)),
            "estuary": bool(data.get("estuary", {}).get(today)),
            "stage": bool(data.get("jenner_stage_history", {}).get(today)),
            "fort_ross": bool(data.get("fort_ross", {}).get(today)),
            "bodega": bool(data.get("bodega_tides", {}).get(today)),
        }
        return available
    
    @staticmethod
    def ensure_backup(data_file="tides.json", backup_dir=".backups"):
        """Keep rotating backups for disaster recovery"""
        try:
            Path(backup_dir).mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"tides_{timestamp}.json")
            
            if os.path.exists(data_file):
                with open(data_file, "r") as f:
                    data = json.load(f)
                with open(backup_file, "w") as f:
                    json.dump(data, f, indent=2)
                
                # Keep only last 50 backups
                backups = sorted(Path(backup_dir).glob("tides_*.json"))
                for old_backup in backups[:-50]:
                    old_backup.unlink()
                
                return backup_file
        except Exception as e:
            print(f"Backup failed: {e}")
        return None
