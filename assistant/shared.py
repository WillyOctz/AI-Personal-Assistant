import os
from datetime import datetime

from assistant import file_index, memory, personality
from assistant.reply import button, copy_button
from assistant.tools import TEXT_EXTENSIONS

def current_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def voice(key, **kw):
    return personality.line(key, verbosity=memory.get_setting("verbosity", "normal"), **kw)

def log_file_search(action, folder_name, query, result_summary):
    memory.add_file_search_event({
        "action": action,
        "folder": folder_name,
        "query": query,
        "result": result_summary,
        "timestamp": current_timestamp(),
    })
    
def build_file_items(folder_name, folder_path, entries):
    items = []

    for entry in entries:
        full_path = entry.get("path") or os.path.join(folder_path, entry["name"])
        
        try:
            rel = os.path.relpath(full_path, folder_path)
        except ValueError:
            rel = entry["name"]
            
        is_folder = entry["type"] == "folder"
        is_text = os.path.splitext(entry["name"])[1].lower() in TEXT_EXTENSIONS
        actions = []
        
        if not is_folder and is_text:
            actions.append(button("Open", f"open file {folder_name} {rel}", style="primary"))
            
        actions.append(button("Reveal", f"reveal file {folder_name} {rel}"))
        
        if is_folder:
            actions.append(button("Pin", f"pin path {full_path} as {entry['name']}", style="ghost"))
            
        actions.append(copy_button("Copy path", full_path))
        
        items.append({"name": entry["name"], "type": entry["type"], "path": full_path,
                      "rel": rel, "actions": actions})
        
    return items

def build_index_items(rows):
    folders = memory.get_search_folders()
    items = []
    
    for row in rows:
        root_path = folders.get(row["root"])
        
        if not root_path:
            continue
        
        entry = {"name": row["name"], "type": "folder" if row["is_dir"] else "file", "path": row["path"]}
        item = build_file_items(row["root"], root_path, [entry])[0]
        item["meta"] = row.get("snip") or file_index.humanize_age(row["mtime"])
        
        pid = row.get("project_id")
        
        if pid:
            item["actions"] = [
                button("Resume", f"resume project #{pid}", style="primary"),
                button("Editor", f"open project #{pid} in editor"),
                button("Reveal", f"reveal file {row['root']} {item['rel']}"),
                button("Pin", f"pin path {row['path']} as {row['name']}", style="ghost"),
                copy_button("Copy path", row["path"]),
            ]
            
        items.append(item)
        
    return items

def build_project_item(project):
    pid = project["id"]
    last = max(project["last_activity"] or 0, project["last_opened"] or 0)
    
    return {
        "id": pid,
        "name": project["name"],
        "path": project["path"],
        "marker": project["marker"],
        "age": file_index.humanize_age(last),
        "actions": [
            button("Resume", f"resume project #{pid}", style="primary"),
            button("Open", f"open project #{pid}"),
            button("Editor", f"open project #{pid} in editor"),
            button("Pin", f"pin path {project['path']} as {project['name']}", style="ghost"),
            copy_button("Copy path", project["path"]),
        ],
    }
