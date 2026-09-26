import json
from pathlib import Path
import smart_organizer as so 

# --- HELPER FUNCTION TESTS ---

def test_get_category():
    assert so.get_category(Path("holiday.jpg")) == "Images"
    assert so.get_category(Path("invoice.pdf")) == "Documents"
    assert so.get_category(Path("script.py")) == "Code"
    assert so.get_category(Path("unknown_file.xyz")) == "Others"

def test_truncate():
    assert so.truncate("short.txt", 15) == "short.txt"
    # Should leave room for the 3 dots
    assert so.truncate("very_long_filename_here.txt", 10) == "very_lo..."

def test_file_hash(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")
    
    # Pre-calculated SHA-256 for the string "hello world"
    expected_hash = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    assert so.file_hash(test_file) == expected_hash

def test_unique_destination(tmp_path):
    dest = tmp_path / "file.txt"
    
    # 1. File doesn't exist yet, should return original path
    assert so.unique_destination(dest) == dest 
    
    # 2. File exists, should append (1)
    dest.write_text("data")
    new_dest = so.unique_destination(dest)
    assert new_dest == tmp_path / "file (1).txt"
    
    # 3. Both exist, should append (2)
    new_dest.write_text("data2")
    newer_dest = so.unique_destination(dest)
    assert newer_dest == tmp_path / "file (2).txt"

# --- CORE LOGIC TESTS ---

def test_organize_standard(tmp_path):
    # Setup: Create dummy files in our temporary folder
    doc_file = tmp_path / "report.docx"
    doc_file.write_text("doc data")
    img_file = tmp_path / "photo.png"
    img_file.write_text("img data")
    
    # Execute: Run the organizer
    so.organize(tmp_path, dry_run=False, by_date=False, skip_dupes=True)
    
    # Assert: Verify files moved from root
    assert not doc_file.exists()
    assert not img_file.exists()
    
    # Assert: Verify files arrived at destinations
    assert (tmp_path / "Documents" / "report.docx").exists()
    assert (tmp_path / "Images" / "photo.png").exists()
    
    # Assert: Verify log file was created
    log_file = tmp_path / so.LOG_NAME
    assert log_file.exists()
    
    # Verify log contents
    log_data = json.loads(log_file.read_text())
    assert len(log_data) == 2
    assert "from" in log_data[0]
    assert "to" in log_data[0]

def test_organize_skip_duplicates(tmp_path):
    # Setup: Create a file that is ALREADY in the target folder
    doc_dir = tmp_path / "Documents"
    doc_dir.mkdir()
    existing_doc = doc_dir / "report.docx"
    existing_doc.write_text("identical content")
    
    # Create the duplicate in the root directory
    new_doc = tmp_path / "report.docx"
    new_doc.write_text("identical content")
    
    # Execute: Run the organizer
    so.organize(tmp_path, dry_run=False, by_date=False, skip_dupes=True)
    
    # Assert: The file in the root should STILL be there because it was skipped
    assert new_doc.exists()
    
    # Assert: No log should be created since no moves happened
    assert not (tmp_path / so.LOG_NAME).exists()

def test_undo_functionality(tmp_path):
    # Setup: Create and move a file
    target_file = tmp_path / "script.py"
    target_file.write_text("print('hello')")
    
    so.organize(tmp_path, dry_run=False, by_date=False, skip_dupes=True)
    
    # Ensure it moved
    assert not target_file.exists()
    assert (tmp_path / "Code" / "script.py").exists()
    
    # Execute: Run undo
    so.undo(tmp_path)
    
    # Assert: File is back in root
    assert target_file.exists()
    
    # Assert: The "Code" directory was removed (cleanup logic)
    assert not (tmp_path / "Code").exists()
    
    # Assert: Log file was deleted
    assert not (tmp_path / so.LOG_NAME).exists()