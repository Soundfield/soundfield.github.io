import json
import os
import re
import sys
import time
import shutil
import zipfile
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from pathlib import Path
import urllib.request
import urllib.error

BASE_DIR = Path(__file__).parent.resolve()
CONTENT_FILE = BASE_DIR / "content.json"
TEMPLATE_FILE = BASE_DIR / "template.html"
OUTPUT_FILE = BASE_DIR / "index.html"
SITEMAP_FILE = BASE_DIR / "sitemap.xml"
FAVICON_FILE = BASE_DIR / "favicon.png"

def resolve_image_url(url):
    if not url: return ''
    url = url.strip()
    if re.search(r'\.(jpe?g|png|gif|webp|svg|bmp)(\?|$)', url, re.I): return url
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
        if not m: m = re.search(r'content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html)
        if m: return m.group(1)
        if 'imgbox.com' in url:
            m = re.search(r'<img[^>]+id=["\']img["\'][^>]+src=["\']([^"\']+)["\']', html)
            if m: return m.group(1)
    except Exception: pass
    return url

DEFAULT_CONTENT = {
    "config": {
        "pageTitle": "Marcelo G. Racca — Audio Director & Sound Designer",
        "name": "Marcelo G. Racca",
        "tagline": "Audio Director • Sound Designer • Audio Postproduction",
        "profilePhoto": "", "ogShareImage": "", "siteUrl": "https://marceloracca.com",
        "reelEmbedUrl": "https://player.vimeo.com/video/714503251?h=79a0928023",
        "footerText": "© 2026 Marcelo Racca — Audio & Media Portfolio",
        "audioCopyright": "© {year} Marcelo G. Racca and respective clients. All rights reserved.",
        "aboutTitle": "About Marcelo",
        "aboutText": "Audio Director and Sound Designer with over 15 years of experience.",
        "gitRepoPath": "",
        "contactLinks": [
            {"label": "LinkedIn", "url": "https://linkedin.com/in/marceloracca/"},
            {"label": "Instagram", "url": "https://www.instagram.com/marcelo_racca/"},
            {"label": "IMDB", "url": "https://www.imdb.com/name/nm6711548/"}
        ],
        "filters": [
            {"key": "category", "label": "Category", "options": [
                {"value": "film", "label": "Film", "tooltip": "Feature films and shorts"},
                {"value": "tv", "label": "TV", "tooltip": "Television series and broadcasts"},
                {"value": "games", "label": "Games", "tooltip": "Video games and interactive media"},
                {"value": "ads", "label": "Advertising", "tooltip": "Commercials and branded content"},
                {"value": "podcast", "label": "Podcasts", "tooltip": "Audio dramas and series"},
                {"value": "apps", "label": "Apps", "tooltip": "Mobile and web applications"},
                {"value": "doc", "label": "Documentaries", "tooltip": "Documentary films"}
            ]},
            {"key": "role", "label": "Role", "options": [
                {"value": "sound-design", "label": "Sound Design", "tooltip": ""},
                {"value": "mix", "label": "Mix", "tooltip": ""},
                {"value": "director", "label": "Director", "tooltip": ""},
                {"value": "composer", "label": "Composer", "tooltip": ""},
                {"value": "interactive", "label": "Interactive Sound", "tooltip": ""},
                {"value": "pm", "label": "Project Manager", "tooltip": ""}
            ]},
            {"key": "studio", "label": "Studio", "options": [
                {"value": "freelance", "label": "Freelance", "tooltip": "Independent freelance work"},
                {"value": "other", "label": "Other", "tooltip": "Studio employment or contracts"}
            ]}
        ]
    },
    "projects": []
}

def load_content():
    if CONTENT_FILE.exists():
        with open(CONTENT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        migrated = False
        cfg = data.get("config", {})
        for fdef in cfg.get("filters", []):
            for opt in fdef.get("options", []):
                if "tooltip" not in opt:
                    opt["tooltip"] = ""
                    migrated = True
        for p in data.get("projects", []):
            for pk, pv in [("visible", True), ("videoEmbed", ""), ("upcoming", False),
                           ("pinned", False), ("audioTracks", []), ("techStack", []),
                           ("extendedDescription", ""), ("galleryImages", [])]:
                if pk not in p:
                    p[pk] = pv
                    migrated = True
        if migrated: save_content(data)
        return data
    save_content(DEFAULT_CONTENT)
    return DEFAULT_CONTENT.copy()

def save_content(data):
    with open(CONTENT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def generate_og_tags(config):
    tags = []
    title = config.get("pageTitle", "")
    desc = config.get("tagline", "")
    photo = config.get("ogShareImage", "") or config.get("profilePhoto", "")
    site_url = config.get("siteUrl", "")
    tags.append(f'<meta property="og:title" content="{title}">')
    tags.append(f'<meta property="og:description" content="{desc}">')
    tags.append('<meta property="og:type" content="website">')
    if site_url: tags.append(f'<meta property="og:url" content="{site_url}">')
    if photo: tags.append(f'<meta property="og:image" content="{photo}">')
    tags.append('<meta name="twitter:card" content="summary_large_image">')
    tags.append(f'<meta name="twitter:title" content="{title}">')
    tags.append(f'<meta name="twitter:description" content="{desc}">')
    if photo: tags.append(f'<meta name="twitter:image" content="{photo}">')
    return "\n".join(tags)

def generate_json_ld(config, projects):
    visible = [p for p in projects if p.get("visible", True)]
    creative_works = []
    for p in visible:
        work = {"@type": "CreativeWork", "name": p.get("title", ""), "description": p.get("description", ""),
                "dateCreated": p.get("year", ""), "genre": p.get("category", "")}
        if p.get("referenceLink"): work["url"] = p["referenceLink"]
        creative_works.append(work)
    person = {
        "@context": "https://schema.org", "@type": "Person",
        "name": config.get("name", ""), "jobTitle": config.get("tagline", ""),
        "url": config.get("siteUrl", ""),
        "image": config.get("ogShareImage", "") or config.get("profilePhoto", ""),
        "sameAs": [l["url"] for l in config.get("contactLinks", []) if l.get("url")],
        "hasOccupation": {"@type": "Occupation", "name": "Audio Director & Sound Designer"},
        "knowsAbout": ["Sound Design", "Audio Post-Production", "Mixing", "Interactive Audio", "Game Audio"],
        "creativeWork": creative_works[:20]
    }
    return '<script type="application/ld+json">\n' + json.dumps(person, indent=2, ensure_ascii=False) + '\n</script>'

def generate_sitemap(config, projects):
    site_url = config.get("siteUrl", "").rstrip("/")
    if not site_url: return ""
    urls = [f"  <url><loc>{site_url}/</loc><priority>1.0</priority></url>"]
    for p in projects:
        if p.get("visible", True) and p.get("referenceLink"):
            urls.append(f"  <url><loc>{p['referenceLink']}</loc><priority>0.7</priority></url>")
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>"

def build_html(config, projects):
    if not TEMPLATE_FILE.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE_FILE}")
    with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        template = f.read()
    visible_projects = [p for p in projects if p.get("visible", True)]
    html = template.replace("__CONFIG_JSON__", json.dumps(config, ensure_ascii=False))
    html = html.replace("__PROJECTS_JSON__", json.dumps(visible_projects, ensure_ascii=False))
    html = html.replace("__OG_META_TAGS__", generate_og_tags(config))
    html = html.replace("__JSON_LD_TAGS__", generate_json_ld(config, projects))
    return html

class PortfolioManagerApp:
    def __init__(self, root):
        self.root = root
        self.base_title = "Portfolio Content Manager"
        self.root.title(self.base_title)
        self.root.geometry("1150x800")
        self.root.minsize(900, 600)
        self.content = load_content()
        self.current_project_index = None
        self.project_dirty = False
        self.profile_dirty = False
        self._audio_names = []
        self._gallery_images = []
        self._thumb_photo = None
        self._fav_photo = None
        self._gallery_preview_photo = None
        self._server_proc = None
        self.project_list_mapping = []
        
        self.search_var = tk.StringVar()
        self.tag_filter_var = tk.StringVar(value="All")

        self._build_menu()
        self._build_notebook()
        self._build_profile_tab()
        self._build_projects_tab()
        self._build_filters_tab()
        self._build_report_tab()
        self._refresh_project_list()
        self._populate_profile_fields()
        self._bind_dirty_tracking()
        self.project_dirty = False
        self.profile_dirty = False
        self._update_title()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        if self._server_proc:
            try: self._server_proc.terminate()
            except Exception: pass
        self.root.destroy()

    def _update_title(self):
        if self.project_dirty or self.profile_dirty:
            self.root.title(f"{self.base_title} • (unsaved)")
        else:
            self.root.title(self.base_title)

    def _mark_project_dirty(self, *args):
        self.project_dirty = True
        self._update_title()

    def _mark_profile_dirty(self, *args):
        self.profile_dirty = True
        self._update_title()

    def _bind_dirty_tracking(self):
        for w in [self.ent_page_title, self.ent_name, self.ent_tagline, self.ent_photo,
                  self.ent_og_image, self.ent_site_url, self.ent_footer,
                  self.ent_about_title, self.ent_reel, self.ent_git_path]:
            w.bind('<KeyRelease>', self._mark_profile_dirty)
        self.txt_about_text.bind('<KeyRelease>', self._mark_profile_dirty)
        self.txt_audio_copyright.bind('<KeyRelease>', self._mark_profile_dirty)
        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)

    def _bind_project_widgets_dirty(self):
        for k, w in self.edit_widgets.items():
            if isinstance(w, (ttk.Entry, ttk.Combobox)):
                w.bind('<KeyRelease>', self._mark_project_dirty)
            elif isinstance(w, tk.Text):
                w.bind('<KeyRelease>', self._mark_project_dirty)
        for w in [self.ent_roles, self.ent_tags, self.ent_tech]:
            w.bind('<KeyRelease>', self._mark_project_dirty)
        self.ent_track_name.bind('<KeyRelease>', self._mark_project_dirty)
        self.txt_extended_desc.bind('<KeyRelease>', self._mark_project_dirty)
        for v in [self.var_visible, self.var_upcoming, self.var_pinned]:
            v.trace_add('write', lambda *a: self._mark_project_dirty())

    def _on_tab_changed(self, event):
        if self.project_dirty and self.current_project_index is not None:
            self._save_current_project(silent=True)
        if self.profile_dirty:
            self._save_profile(silent=True)
        if hasattr(self, 'report_frame'):
            self._refresh_report()

    def _bind_mousewheel(self):
        if sys.platform == 'win32':
            self.edit_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        else:
            self.edit_canvas.bind_all("<Button-4>", self._on_mousewheel)
            self.edit_canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_mousewheel(self):
        if sys.platform == 'win32':
            self.edit_canvas.unbind_all("<MouseWheel>")
        else:
            self.edit_canvas.unbind_all("<Button-4>")
            self.edit_canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        if sys.platform == 'win32':
            self.edit_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        elif sys.platform == 'darwin':
            self.edit_canvas.yview_scroll(int(-1*event.delta), "units")
        else:
            if event.num == 4:
                self.edit_canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.edit_canvas.yview_scroll(1, "units")

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        fm = tk.Menu(menubar, tearoff=0)
        fm.add_command(label="Open HTML Output...", command=self.open_output, accelerator="Ctrl+O")
        fm.add_command(label="Save & Copy to Repo", command=self.save_website, accelerator="Ctrl+S")
        fm.add_command(label="Preview Locally", command=self.preview_locally, accelerator="Ctrl+P")
        fm.add_command(label="Export as ZIP...", command=self.export_zip)
        fm.add_separator()
        fm.add_command(label="Export JSON Backup...", command=self.export_backup)
        fm.add_command(label="Import JSON Backup...", command=self.import_backup)
        fm.add_separator()
        fm.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=fm)
        self.root.config(menu=menubar)
        self.root.bind('<Control-s>', lambda e: self.save_website())
        self.root.bind('<Control-o>', lambda e: self.open_output())
        self.root.bind('<Control-p>', lambda e: self.preview_locally())

    def open_output(self):
        if OUTPUT_FILE.exists():
            import webbrowser
            webbrowser.open(OUTPUT_FILE.as_uri())
        else:
            messagebox.showinfo("Not Found", "No output file yet. Press Ctrl+S first.")

    def preview_locally(self):
        if self.current_project_index is not None and self.project_dirty:
            self._save_current_project(silent=True)
        if self.profile_dirty:
            self._save_profile(silent=True)
        try:
            html = build_html(self.content["config"], self.content["projects"])
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f: f.write(html)
            sitemap = generate_sitemap(self.content["config"], self.content["projects"])
            if sitemap:
                with open(SITEMAP_FILE, 'w', encoding='utf-8') as f: f.write(sitemap)
            save_content(self.content)
            self.project_dirty = False
            self.profile_dirty = False
            self._update_title()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save:\n{str(e)}")
            return

        if self._server_proc:
            try: self._server_proc.terminate(); time.sleep(0.3)
            except Exception: pass

        port = 8000
        try:
            kwargs = {'cwd': str(BASE_DIR), 'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL}
            if sys.platform == 'win32': kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            self._server_proc = subprocess.Popen([sys.executable, '-m', 'http.server', str(port)], **kwargs)
            time.sleep(0.5)
            import webbrowser
            webbrowser.open(f'http://localhost:{port}')
        except Exception as e:
            messagebox.showerror("Preview Error", f"Could not start local server:\n{str(e)}")

    def save_website(self):
        if self.current_project_index is not None and self.project_dirty:
            self._save_current_project(silent=True)
        if self.profile_dirty:
            self._save_profile(silent=True)
        try:
            html = build_html(self.content["config"], self.content["projects"])
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f: f.write(html)
            sitemap = generate_sitemap(self.content["config"], self.content["projects"])
            if sitemap:
                with open(SITEMAP_FILE, 'w', encoding='utf-8') as f: f.write(sitemap)
            save_content(self.content)
            
            cleanup_result = self._cleanup_orphaned_files()
            
            self.project_dirty = False
            self.profile_dirty = False
            self._update_title()
            msg_parts = [f"Generated:\n• {OUTPUT_FILE.name}"]
            if sitemap: msg_parts.append(f"• {SITEMAP_FILE.name}")
            if cleanup_result: msg_parts.append(f"\n🧹 {cleanup_result}")
                
            git_path = self.content["config"].get("gitRepoPath", "").strip()
            if git_path:
                repo = Path(git_path)
                if repo.exists() and (repo / ".git").exists():
                    for fn in ["index.html", "sitemap.xml", "favicon.png"]:
                        src = BASE_DIR / fn
                        if src.exists(): shutil.copy2(src, repo / fn)
                    for folder in ["images", "audio"]:
                        src_d = BASE_DIR / folder
                        dst_d = repo / folder
                        if src_d.exists():
                            if dst_d.exists(): shutil.rmtree(dst_d)
                            shutil.copytree(src_d, dst_d)
                    msg_parts.append(f"\nCopied to repo:\n{git_path}\n\n⚡ Run GitHub Desktop to sync.")
                else:
                    msg_parts.append(f"\n⚠️ Repo path invalid or not a Git repo:\n{git_path}")
            else:
                msg_parts.append("\n💡 Set Git repo path in Profile tab to auto-copy.")
            messagebox.showinfo("Saved ✓", "\n".join(msg_parts))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save:\n{str(e)}")

    def _cleanup_orphaned_files(self):
        referenced = set()
        cfg = self.content.get("config", {})
        for key in ["profilePhoto", "ogShareImage"]:
            val = cfg.get(key, "")
            if val and (val.startswith("images/") or val.startswith("audio/")):
                referenced.add(val.replace("\\", "/"))
        for p in self.content.get("projects", []):
            poster = p.get("poster", "")
            if poster and (poster.startswith("images/") or poster.startswith("audio/")):
                referenced.add(poster.replace("\\", "/"))
            for track in p.get("audioTracks", []):
                url = track.get("url", "") if isinstance(track, dict) else str(track)
                if url and (url.startswith("images/") or url.startswith("audio/")):
                    referenced.add(url.replace("\\", "/"))
            for img in p.get("galleryImages", []):
                if img and (img.startswith("images/") or img.startswith("audio/")):
                    referenced.add(img.replace("\\", "/"))

        orphans = []
        for folder in ["images", "audio"]:
            d = BASE_DIR / folder
            if d.exists():
                for f in d.rglob("*"):
                    if f.is_file():
                        rel_path = f"{folder}/{f.relative_to(d).as_posix()}"
                        if rel_path not in referenced:
                            orphans.append((rel_path, f))

        if orphans:
            msg = "Found unused files in /images and /audio:\n\n"
            msg += "\n".join([f"• {o[0]}" for o in orphans[:10]])
            if len(orphans) > 10: msg += f"\n... and {len(orphans) - 10} more."
            msg += "\n\nDelete these unused files?"
            if messagebox.askyesno("Cleanup Unused Files", msg):
                deleted_count = 0
                for rel_path, abs_path in orphans:
                    try: abs_path.unlink(); deleted_count += 1
                    except Exception: pass
                return f"Deleted {deleted_count} unused files."
        return None

    def export_zip(self):
        path = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("ZIP files", "*.zip")], initialfile="portfolio-site.zip")
        if not path: return
        try:
            with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
                if OUTPUT_FILE.exists(): zf.write(OUTPUT_FILE, "index.html")
                if SITEMAP_FILE.exists(): zf.write(SITEMAP_FILE, "sitemap.xml")
                if FAVICON_FILE.exists(): zf.write(FAVICON_FILE, "favicon.png")
                for folder in ["images", "audio"]:
                    d = BASE_DIR / folder
                    if d.exists():
                        for f in d.rglob("*"):
                            if f.is_file(): zf.write(f, f"{folder}/{f.relative_to(d)}")
            messagebox.showinfo("Exported ✓", f"ZIP saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def export_backup(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")], initialfile="portfolio_backup.json")
        if path:
            with open(path, 'w', encoding='utf-8') as f: json.dump(self.content, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Exported", f"Backup saved to:\n{path}")

    def import_backup(self):
        path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f: self.content = json.load(f)
                save_content(self.content)
                self._populate_profile_fields()
                self._refresh_project_list()
                self.project_dirty = False
                self.profile_dirty = False
                self._update_title()
                messagebox.showinfo("Imported", "Content imported successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import:\n{str(e)}")

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        self.profile_tab = ttk.Frame(self.notebook)
        self.projects_tab = ttk.Frame(self.notebook)
        self.filters_tab = ttk.Frame(self.notebook)
        self.report_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.profile_tab, text="Profile")
        self.notebook.add(self.projects_tab, text="Projects")
        self.notebook.add(self.filters_tab, text="Filter Options")
        self.notebook.add(self.report_tab, text="Report")

    def _resolve_into(self, entry_widget):
        original = entry_widget.get().strip()
        if not original:
            messagebox.showinfo("Resolve", "Enter a URL first.")
            return
        entry_widget.delete(0, 'end')
        entry_widget.insert(0, "Resolving...")
        self.root.update_idletasks()
        resolved = resolve_image_url(original)
        entry_widget.delete(0, 'end')
        entry_widget.insert(0, resolved)
        self._mark_profile_dirty() 
        if resolved != original:
            messagebox.showinfo("Resolved ✓", f"Direct URL:\n{resolved}")
        else:
            messagebox.showwarning("Not Resolved", "Host blocked scraper. Try 'Browse Local'.")

    def _browse_image(self, entry_widget):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.webp *.gif *.svg")])
        if path:
            img_dir = BASE_DIR / "images"
            img_dir.mkdir(exist_ok=True)
            filename = Path(path).name
            dest = img_dir / filename
            if dest.exists():
                stem = Path(filename).stem
                suffix = Path(filename).suffix
                filename = f"{stem}_{int(time.time())}{suffix}"
                dest = img_dir / filename
            shutil.copy(path, dest)
            rel = f"images/{dest.name}"
            entry_widget.delete(0, 'end')
            entry_widget.insert(0, rel)
            self._mark_profile_dirty()
            self._update_thumbnail(rel)
            messagebox.showinfo("Image Added", f"Copied to /images.\nURL: {rel}")

    def _browse_favicon(self):
        path = filedialog.askopenfilename(filetypes=[("PNG Image", "*.png")])
        if path:
            dest = BASE_DIR / "favicon.png"
            try:
                shutil.copy(path, dest)
                self._update_favicon_preview()
                self._mark_profile_dirty()
                messagebox.showinfo("Favicon Updated", "favicon.png has been updated.\nIt will be copied to your repo on next Save.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to copy favicon:\n{str(e)}")

    def _update_favicon_preview(self):
        if not hasattr(self, 'fav_preview_label'): return
        fav_path = BASE_DIR / "favicon.png"
        if fav_path.exists():
            try:
                from PIL import Image, ImageTk
                img = Image.open(fav_path)
                img.thumbnail((32, 32))
                self._fav_photo = ImageTk.PhotoImage(img)
                self.fav_preview_label.config(image=self._fav_photo, text='')
            except ImportError:
                self.fav_preview_label.config(image='', text='(PIL needed)')
            except Exception:
                self.fav_preview_label.config(image='', text='Error')
        else:
            self.fav_preview_label.config(image='', text='No favicon')

    def _browse_gallery_image(self):
        paths = filedialog.askopenfilenames(filetypes=[("Image files", "*.jpg *.jpeg *.png *.webp *.gif *.svg")])
        if paths:
            img_dir = BASE_DIR / "images"
            img_dir.mkdir(exist_ok=True)
            for p in paths:
                filename = Path(p).name
                dest = img_dir / filename
                if dest.exists():
                    stem = Path(filename).stem
                    suffix = Path(filename).suffix
                    filename = f"{stem}_{int(time.time())}{suffix}"
                    dest = img_dir / filename
                shutil.copy(p, dest)
                rel = f"images/{dest.name}"
                self.gallery_listbox.insert('end', rel)
                self._gallery_images.append(rel)
            self._mark_project_dirty()
            last_idx = self.gallery_listbox.size() - 1
            self.gallery_listbox.selection_clear(0, 'end')
            self.gallery_listbox.selection_set(last_idx)
            self._update_gallery_preview(self._gallery_images[last_idx])

    def _browse_audio(self):
        paths = filedialog.askopenfilenames(filetypes=[("Audio files", "*.mp3 *.wav *.ogg *.m4a")])
        if paths:
            audio_dir = BASE_DIR / "audio"
            audio_dir.mkdir(exist_ok=True)
            for p in paths:
                dest = audio_dir / Path(p).name
                shutil.copy(p, dest)
                self.audio_listbox.insert('end', f"audio/{dest.name}")
                self._audio_names.append("")
            self._mark_project_dirty()

    def _browse_git_repo(self):
        path = filedialog.askdirectory(title="Select Git Repository Folder")
        if path:
            self.ent_git_path.delete(0, 'end')
            self.ent_git_path.insert(0, path)
            self._mark_profile_dirty()

    def _update_thumbnail(self, url):
        if not hasattr(self, 'thumb_label'): return
        if not url or not str(url).startswith("images/"):
            self.thumb_label.config(image='', text='No preview')
            return
        img_path = BASE_DIR / url
        if img_path.exists():
            try:
                from PIL import Image, ImageTk
                img = Image.open(img_path)
                img.thumbnail((120, 68))
                self._thumb_photo = ImageTk.PhotoImage(img)
                self.thumb_label.config(image=self._thumb_photo, text='')
            except ImportError:
                self.thumb_label.config(image='', text='(PIL needed\nfor preview)')
        else:
            self.thumb_label.config(image='', text='File not found')

    def _update_gallery_preview(self, rel_path):
        if not hasattr(self, 'gallery_preview_label'): return
        if not rel_path or not str(rel_path).startswith("images/"):
            self.gallery_preview_label.config(image='', text='No preview')
            return
        img_path = BASE_DIR / rel_path
        if img_path.exists():
            try:
                from PIL import Image, ImageTk
                img = Image.open(img_path)
                img.thumbnail((160, 90))
                self._gallery_preview_photo = ImageTk.PhotoImage(img)
                self.gallery_preview_label.config(image=self._gallery_preview_photo, text='')
            except ImportError:
                self.gallery_preview_label.config(image='', text='(PIL needed)')
        else:
            self.gallery_preview_label.config(image='', text='File not found')

    def _build_profile_tab(self):
        canvas = tk.Canvas(self.profile_tab)
        scrollbar = ttk.Scrollbar(self.profile_tab, orient='vertical', command=canvas.yview)
        self.profile_frame = ttk.Frame(canvas)
        self.profile_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        cw = canvas.create_window((0, 0), window=self.profile_frame, anchor="nw")
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(cw, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        PAD_X = 10
        PAD_Y = 3

        ttk.Label(self.profile_frame, text="Identity", font=('', 14, 'bold')).grid(row=0, column=0, sticky='w', padx=PAD_X, pady=(10, 5), columnspan=4)
        ttk.Label(self.profile_frame, text="Page Title:").grid(row=1, column=0, sticky='w', padx=PAD_X, pady=PAD_Y)
        self.ent_page_title = ttk.Entry(self.profile_frame, width=30)
        self.ent_page_title.grid(row=1, column=1, sticky='ew', padx=4, pady=PAD_Y)
        ttk.Label(self.profile_frame, text="Your Name:").grid(row=1, column=2, sticky='w', padx=(16, PAD_X), pady=PAD_Y)
        self.ent_name = ttk.Entry(self.profile_frame, width=30)
        self.ent_name.grid(row=1, column=3, sticky='ew', padx=4, pady=PAD_Y)
        ttk.Label(self.profile_frame, text="Tagline:").grid(row=2, column=0, sticky='w', padx=PAD_X, pady=PAD_Y)
        self.ent_tagline = ttk.Entry(self.profile_frame, width=30)
        self.ent_tagline.grid(row=2, column=1, sticky='ew', padx=4, pady=PAD_Y)
        ttk.Label(self.profile_frame, text="Site URL:").grid(row=2, column=2, sticky='w', padx=(16, PAD_X), pady=PAD_Y)
        self.ent_site_url = ttk.Entry(self.profile_frame, width=30)
        self.ent_site_url.grid(row=2, column=3, sticky='ew', padx=4, pady=PAD_Y)
        ttk.Label(self.profile_frame, text="Footer Text:").grid(row=3, column=0, sticky='w', padx=PAD_X, pady=PAD_Y)
        self.ent_footer = ttk.Entry(self.profile_frame, width=30)
        self.ent_footer.grid(row=3, column=1, sticky='ew', padx=4, pady=PAD_Y)
        ttk.Label(self.profile_frame, text="Profile Photo:").grid(row=4, column=0, sticky='w', padx=PAD_X, pady=PAD_Y)
        photo_frame = ttk.Frame(self.profile_frame)
        photo_frame.grid(row=4, column=1, columnspan=3, sticky='ew', padx=4, pady=PAD_Y)
        self.ent_photo = ttk.Entry(photo_frame, width=35)
        self.ent_photo.pack(side='left', fill='x', expand=True)
        ttk.Button(photo_frame, text="Resolve", width=8, command=lambda: self._resolve_into(self.ent_photo)).pack(side='left', padx=2)
        ttk.Button(photo_frame, text="📁 Browse", width=10, command=lambda: self._browse_image(self.ent_photo)).pack(side='left')
        ttk.Label(self.profile_frame, text="Share Image:").grid(row=5, column=0, sticky='w', padx=PAD_X, pady=PAD_Y)
        share_frame = ttk.Frame(self.profile_frame)
        share_frame.grid(row=5, column=1, columnspan=3, sticky='ew', padx=4, pady=PAD_Y)
        self.ent_og_image = ttk.Entry(share_frame, width=35)
        self.ent_og_image.pack(side='left', fill='x', expand=True)
        ttk.Button(share_frame, text="Resolve", width=8, command=lambda: self._resolve_into(self.ent_og_image)).pack(side='left', padx=2)
        ttk.Button(share_frame, text="📁 Browse", width=10, command=lambda: self._browse_image(self.ent_og_image)).pack(side='left')
        
        # Favicon
        ttk.Label(self.profile_frame, text="Favicon (.png):").grid(row=6, column=0, sticky='w', padx=PAD_X, pady=PAD_Y)
        fav_frame = ttk.Frame(self.profile_frame)
        fav_frame.grid(row=6, column=1, columnspan=3, sticky='ew', padx=4, pady=PAD_Y)
        self.fav_preview_label = ttk.Label(fav_frame, text='No favicon', relief='solid', anchor='center', width=4)
        self.fav_preview_label.pack(side='left', padx=(0, 8))
        ttk.Button(fav_frame, text="📁 Browse PNG", width=14, command=self._browse_favicon).pack(side='left')

        self.profile_frame.columnconfigure(1, weight=1)
        self.profile_frame.columnconfigure(3, weight=1)

        ttk.Separator(self.profile_frame, orient='horizontal').grid(row=7, column=0, columnspan=4, sticky='ew', pady=12, padx=PAD_X)
        ttk.Label(self.profile_frame, text="About Me", font=('', 14, 'bold')).grid(row=8, column=0, sticky='w', padx=PAD_X, pady=5, columnspan=4)
        ttk.Label(self.profile_frame, text="About Title:").grid(row=9, column=0, sticky='w', padx=PAD_X, pady=PAD_Y)
        self.ent_about_title = ttk.Entry(self.profile_frame, width=30)
        self.ent_about_title.grid(row=9, column=1, columnspan=3, sticky='ew', padx=4, pady=PAD_Y)
        ttk.Label(self.profile_frame, text="About Text:").grid(row=10, column=0, sticky='nw', padx=PAD_X, pady=PAD_Y)
        self.txt_about_text = tk.Text(self.profile_frame, width=60, height=5)
        self.txt_about_text.grid(row=10, column=1, columnspan=3, sticky='ew', padx=4, pady=PAD_Y)

        ttk.Separator(self.profile_frame, orient='horizontal').grid(row=11, column=0, columnspan=4, sticky='ew', pady=12, padx=PAD_X)
        ttk.Label(self.profile_frame, text="Showreel", font=('', 14, 'bold')).grid(row=12, column=0, sticky='w', padx=PAD_X, pady=5, columnspan=4)
        ttk.Label(self.profile_frame, text="Video Embed URL:").grid(row=13, column=0, sticky='w', padx=PAD_X, pady=PAD_Y)
        self.ent_reel = ttk.Entry(self.profile_frame, width=30)
        self.ent_reel.grid(row=13, column=1, columnspan=3, sticky='ew', padx=4, pady=PAD_Y)

        ttk.Separator(self.profile_frame, orient='horizontal').grid(row=14, column=0, columnspan=4, sticky='ew', pady=12, padx=PAD_X)
        ttk.Label(self.profile_frame, text="Copyright Notice", font=('', 14, 'bold')).grid(row=15, column=0, sticky='w', padx=PAD_X, pady=5, columnspan=4)
        self.txt_audio_copyright = tk.Text(self.profile_frame, width=60, height=4)
        self.txt_audio_copyright.grid(row=16, column=0, columnspan=4, sticky='ew', padx=PAD_X, pady=PAD_Y)

        ttk.Separator(self.profile_frame, orient='horizontal').grid(row=17, column=0, columnspan=4, sticky='ew', pady=12, padx=PAD_X)
        ttk.Label(self.profile_frame, text="Git Deployment", font=('', 14, 'bold')).grid(row=18, column=0, sticky='w', padx=PAD_X, pady=5, columnspan=4)
        ttk.Label(self.profile_frame, text="Repo Path:").grid(row=19, column=0, sticky='w', padx=PAD_X, pady=PAD_Y)
        git_frame = ttk.Frame(self.profile_frame)
        git_frame.grid(row=19, column=1, columnspan=3, sticky='ew', padx=4, pady=PAD_Y)
        self.ent_git_path = ttk.Entry(git_frame, width=35)
        self.ent_git_path.pack(side='left', fill='x', expand=True)
        ttk.Button(git_frame, text="📁 Browse", width=10, command=self._browse_git_repo).pack(side='left')

        ttk.Separator(self.profile_frame, orient='horizontal').grid(row=20, column=0, columnspan=4, sticky='ew', pady=12, padx=PAD_X)
        ttk.Label(self.profile_frame, text="Contact / Social Links", font=('', 14, 'bold')).grid(row=21, column=0, sticky='w', padx=PAD_X, pady=5, columnspan=4)
        self.links_frame = ttk.Frame(self.profile_frame)
        self.links_frame.grid(row=22, column=0, columnspan=4, sticky='ew', padx=PAD_X)
        self.links_frame.columnconfigure(0, weight=1)
        self.links_frame.columnconfigure(1, weight=2)
        self.link_entries = []
        self._rebuild_link_rows()
        btn_row = ttk.Frame(self.profile_frame)
        btn_row.grid(row=23, column=0, columnspan=4, pady=10)
        ttk.Button(btn_row, text="+ Add Link", command=self._add_link_row).pack(side='left', padx=5)
        ttk.Button(btn_row, text="Apply Profile Changes", command=lambda: self._save_profile()).pack(side='left', padx=5)

    def _rebuild_link_rows(self):
        for w in self.links_frame.winfo_children(): w.destroy()
        self.link_entries = []
        ttk.Label(self.links_frame, text="Label", font=('', 9, 'bold')).grid(row=0, column=0, sticky='w')
        ttk.Label(self.links_frame, text="URL", font=('', 9, 'bold')).grid(row=0, column=1, sticky='w')
        for link in self.content["config"]["contactLinks"]:
            self._add_link_row(link.get("label", ""), link.get("url", ""))

    def _add_link_row(self, label="", url=""):
        ri = len(self.link_entries) + 1
        el = ttk.Entry(self.links_frame, width=20)
        el.insert(0, label)
        el.grid(row=ri, column=0, sticky='ew', padx=2, pady=2)
        el.bind('<KeyRelease>', self._mark_profile_dirty)
        eu = ttk.Entry(self.links_frame, width=60)
        eu.insert(0, url)
        eu.grid(row=ri, column=1, sticky='ew', padx=2, pady=2)
        eu.bind('<KeyRelease>', self._mark_profile_dirty)
        btn = ttk.Button(self.links_frame, text="✕", width=3, command=lambda r=ri: self._remove_link_row(r))
        btn.grid(row=ri, column=2, padx=2)
        self.link_entries.append((el, eu, btn))

    def _remove_link_row(self, row_idx):
        current = [(l.get(), u.get()) for (l, u, _) in self.link_entries]
        del current[row_idx - 1]
        self.content["config"]["contactLinks"] = [{"label": l, "url": u} for l, u in current]
        self._rebuild_link_rows()
        self._mark_profile_dirty()

    def _populate_profile_fields(self):
        c = self.content["config"]
        for attr, key in [("ent_page_title", "pageTitle"), ("ent_name", "name"), ("ent_tagline", "tagline"),
                          ("ent_photo", "profilePhoto"), ("ent_og_image", "ogShareImage"), ("ent_site_url", "siteUrl"),
                          ("ent_footer", "footerText"), ("ent_about_title", "aboutTitle"),
                          ("ent_reel", "reelEmbedUrl"), ("ent_git_path", "gitRepoPath")]:
            getattr(self, attr).delete(0, 'end')
            getattr(self, attr).insert(0, c.get(key, ""))
        self.txt_about_text.delete('1.0', 'end')
        self.txt_about_text.insert('1.0', c.get("aboutText", ""))
        self.txt_audio_copyright.delete('1.0', 'end')
        self.txt_audio_copyright.insert('1.0', c.get("audioCopyright", ""))
        self._rebuild_link_rows()
        self._update_favicon_preview()

    def _save_profile(self, silent=False):
        c = self.content["config"]
        c["pageTitle"] = self.ent_page_title.get().strip()
        c["name"] = self.ent_name.get().strip()
        c["tagline"] = self.ent_tagline.get().strip()
        c["profilePhoto"] = self.ent_photo.get().strip()
        c["ogShareImage"] = self.ent_og_image.get().strip()
        c["siteUrl"] = self.ent_site_url.get().strip()
        c["footerText"] = self.ent_footer.get().strip()
        c["aboutTitle"] = self.ent_about_title.get().strip()
        c["aboutText"] = self.txt_about_text.get('1.0', 'end').strip()
        c["audioCopyright"] = self.txt_audio_copyright.get('1.0', 'end').strip()
        c["reelEmbedUrl"] = self.ent_reel.get().strip()
        c["gitRepoPath"] = self.ent_git_path.get().strip()
        c["contactLinks"] = [{"label": l.get().strip(), "url": u.get().strip()} for l, u, _ in self.link_entries if l.get().strip() and u.get().strip()]
        save_content(self.content)
        self.profile_dirty = False
        self._update_title()
        if not silent:
            messagebox.showinfo("Profile Saved", "Profile changes saved.")

    def _build_projects_tab(self):
        left = ttk.Frame(self.projects_tab, width=320)
        left.pack(side='left', fill='y', padx=5, pady=5)
        left.pack_propagate(False)
        
        search_frame = ttk.Frame(left)
        search_frame.pack(fill='x', padx=5, pady=(5, 0))
        ttk.Label(search_frame, text="Search:").pack(side='left', padx=(0, 5))
        self.search_var.trace_add("write", self._on_search_changed)
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side='left', fill='x', expand=True)

        title_frame = ttk.Frame(left)
        title_frame.pack(fill='x', padx=5, pady=(10, 0))
        ttk.Label(title_frame, text="Projects", font=('', 12, 'bold')).pack(side='left')
        
        self.tag_filter_var.trace_add("write", self._on_search_changed)
        
        filter_options = ["All"]
        for f in self.content["config"]["filters"]:
            if f["key"] in ["category", "role"]:
                for opt in f["options"]:
                    filter_options.append(opt["label"])
                    
        self.tag_filter_combo = ttk.Combobox(title_frame, textvariable=self.tag_filter_var, values=filter_options, state="readonly", width=14)
        self.tag_filter_combo.pack(side='right')

        lf = ttk.Frame(left)
        lf.pack(fill='both', expand=True, padx=5, pady=5)
        self.project_listbox = tk.Listbox(lf, font=('', 10), selectmode='extended')
        self.project_listbox.pack(side='left', fill='both', expand=True)
        sb = ttk.Scrollbar(lf, orient='vertical', command=self.project_listbox.yview)
        sb.pack(side='right', fill='y')
        self.project_listbox.config(yscrollcommand=sb.set)
        self.project_listbox.bind('<<ListboxSelect>>', self._on_project_select)
        bf = ttk.Frame(left)
        bf.pack(fill='x', padx=5, pady=5)
        ttk.Button(bf, text="+ New Project", command=self._new_project).pack(fill='x', pady=2)
        ttk.Button(bf, text="Duplicate", command=self._duplicate_project).pack(fill='x', pady=2)
        ttk.Button(bf, text="↑ Move Up", command=lambda: self._move_project(-1)).pack(side='left', fill='x', expand=True, padx=2)
        ttk.Button(bf, text="↓ Move Down", command=lambda: self._move_project(1)).pack(side='left', fill='x', expand=True, padx=2)
        ttk.Button(bf, text="Delete", command=self._delete_project).pack(fill='x', pady=(5, 0))
        ttk.Button(bf, text="📋 Bulk Edit Tags", command=self._bulk_edit).pack(fill='x', pady=(5, 0))

        right = ttk.Frame(self.projects_tab)
        right.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        
        self.edit_canvas = tk.Canvas(right)
        scrollbar = ttk.Scrollbar(right, orient='vertical', command=self.edit_canvas.yview)
        self.edit_frame = ttk.Frame(self.edit_canvas)
        self.edit_frame.bind("<Configure>", lambda e: self.edit_canvas.configure(scrollregion=self.edit_canvas.bbox("all")))
        ecw = self.edit_canvas.create_window((0, 0), window=self.edit_frame, anchor="nw")
        self.edit_canvas.bind('<Configure>', lambda e: self.edit_canvas.itemconfig(ecw, width=e.width))
        self.edit_canvas.configure(yscrollcommand=scrollbar.set)
        self.edit_canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        self.edit_canvas.bind('<Enter>', lambda e: self._bind_mousewheel())
        self.edit_canvas.bind('<Leave>', lambda e: self._unbind_mousewheel())
        
        self._build_edit_form()

    def _on_search_changed(self, *args):
        query = self.search_var.get().lower().strip()
        selected_tag = self.tag_filter_var.get()
        
        self.project_listbox.delete(0, 'end')
        self.project_list_mapping = []
        
        tag_value = None
        tag_key = None
        if selected_tag != "All":
            for f in self.content["config"]["filters"]:
                for opt in f["options"]:
                    if opt["label"] == selected_tag:
                        tag_value = opt["value"]
                        tag_key = f["key"]
                        break
                if tag_value: break

        for idx, p in enumerate(self.content["projects"]):
            if tag_value:
                if tag_key == "category" and p.get("category") != tag_value:
                    continue
                elif tag_key == "role" and tag_value not in p.get("roles", []):
                    continue
                    
            searchable = f"{p.get('title','')} {p.get('category','')} {p.get('year','')} {' '.join(p.get('tags',[]))} {p.get('description','')} {' '.join(p.get('roles', []))}".lower()
            if query and query not in searchable:
                continue
                
            t = p.get('title', '(Untitled)')
            c = p.get('category', '').upper()
            y = p.get('year', '')
            v = p.get('visible', True)
            u = p.get('upcoming', False)
            has_ext = bool(p.get('extendedDescription', '').strip() or p.get('galleryImages', []))
            prefix = "+ " if has_ext else "  "
            s = ""
            if not v: s = "  ⏸️ Hidden"
            elif u: s = "  🚀 Upcoming"
            self.project_listbox.insert('end', f"{prefix}{t} [{c}] {y}{s}")
            self.project_list_mapping.append(idx)

    def _refresh_project_list(self):
        self._on_search_changed()

    def _bulk_edit(self):
        sel = self.project_listbox.curselection()
        if not sel:
            messagebox.showinfo("Bulk Edit", "Select one or more projects first.")
            return
        win = tk.Toplevel(self.root)
        win.title("Bulk Edit Tags")
        win.geometry("400x200")
        win.transient(self.root)
        ttk.Label(win, text=f"Editing {len(sel)} projects", font=('', 12, 'bold')).pack(pady=10)
        ttk.Label(win, text="Add tags (comma-separated):").pack(anchor='w', padx=20)
        add_tags = ttk.Entry(win, width=40)
        add_tags.pack(padx=20, pady=2)
        ttk.Label(win, text="Remove tags (comma-separated):").pack(anchor='w', padx=20)
        rem_tags = ttk.Entry(win, width=40)
        rem_tags.pack(padx=20, pady=2)
        def apply():
            at = [t.strip() for t in add_tags.get().split(",") if t.strip()]
            rt = [t.strip() for t in rem_tags.get().split(",") if t.strip()]
            for list_idx in sel:
                real_idx = self.project_list_mapping[list_idx]
                p = self.content["projects"][real_idx]
                tags = p.get("tags", [])
                for t in at:
                    if t not in tags: tags.append(t)
                p["tags"] = [t for t in tags if t not in rt]
            save_content(self.content)
            self._refresh_project_list()
            win.destroy()
            messagebox.showinfo("Done", f"Updated {len(sel)} projects.")
        ttk.Button(win, text="Apply", command=apply).pack(pady=15)

    def _build_edit_form(self):
        f = self.edit_frame
        for w in f.winfo_children(): w.destroy()
        self.edit_widgets = {}
        PX = 8
        PY = 3
        tf = ttk.Frame(f)
        tf.grid(row=0, column=0, columnspan=6, sticky='w', padx=PX, pady=(8, 4))
        self.var_visible = tk.BooleanVar(value=True)
        ttk.Checkbutton(tf, text="✅ Visible", variable=self.var_visible).pack(side='left', padx=(0, 15))
        self.var_pinned = tk.BooleanVar(value=False)
        ttk.Checkbutton(tf, text="⭐ Pinned", variable=self.var_pinned).pack(side='left', padx=(0, 15))
        self.var_upcoming = tk.BooleanVar(value=False)
        ttk.Checkbutton(tf, text="🚀 Upcoming", variable=self.var_upcoming).pack(side='left')

        fields_left = [
            ("title", "Title:", "entry"),
            ("category", "Category:", "combo", ["film", "tv", "games", "ads", "podcast", "apps", "doc"]),
            ("studio", "Studio Key:", "combo", ["freelance", "NonStop", "Illusion Studios", "Bamba Music", "CIVISA", "Pura"]),
            ("studioLabel", "Studio Label:", "entry"),
            ("year", "Year:", "entry"),
            ("meta", "Meta Info:", "entry"),
        ]
        fields_right = [
            ("referenceLink", "Reference URL:", "entry"),
            ("referenceLinkText", "Ref Button Text:", "entry"),
        ]
        sr = 1
        for i, spec in enumerate(fields_left):
            row = sr + i
            key, lt, ft = spec[0], spec[1], spec[2]
            ttk.Label(f, text=lt).grid(row=row, column=0, sticky='w', padx=PX, pady=PY)
            if ft == "entry":
                w = ttk.Entry(f, width=28)
                w.grid(row=row, column=1, sticky='ew', padx=4, pady=PY)
            elif ft == "combo":
                w = ttk.Combobox(f, values=spec[3], width=25)
                w.grid(row=row, column=1, sticky='ew', padx=4, pady=PY)
            self.edit_widgets[key] = w
        for i, spec in enumerate(fields_right):
            row = sr + i
            key, lt, ft = spec[0], spec[1], spec[2]
            ttk.Label(f, text=lt).grid(row=row, column=2, sticky='w', padx=(16, PX), pady=PY)
            w = ttk.Entry(f, width=28)
            w.grid(row=row, column=3, sticky='ew', padx=4, pady=PY)
            self.edit_widgets[key] = w
        f.columnconfigure(1, weight=1)
        f.columnconfigure(3, weight=1)

        desc_row = sr + len(fields_left)
        ttk.Label(f, text="Description:").grid(row=desc_row, column=0, sticky='nw', padx=PX, pady=PY)
        desc_w = tk.Text(f, width=60, height=4)
        desc_w.grid(row=desc_row, column=1, columnspan=3, sticky='ew', padx=4, pady=PY)
        self.edit_widgets["description"] = desc_w

        poster_row = desc_row + 1
        ttk.Separator(f, orient='horizontal').grid(row=poster_row, column=0, columnspan=6, sticky='ew', pady=6, padx=PX)
        poster_row += 1
        poster_frame = ttk.Frame(f)
        poster_frame.grid(row=poster_row, column=0, columnspan=6, sticky='ew', padx=PX, pady=PY)
        self.thumb_label = ttk.Label(poster_frame, text='No preview', relief='solid', anchor='center', width=16)
        self.thumb_label.pack(side='left', padx=(0, 8))
        poster_inputs = ttk.Frame(poster_frame)
        poster_inputs.pack(side='left', fill='x', expand=True)
        ttk.Label(poster_inputs, text="Poster Image:").pack(anchor='w')
        pr_entry = ttk.Entry(poster_inputs, width=40)
        pr_entry.pack(fill='x', pady=2)
        self.edit_widgets["poster"] = pr_entry
        pr_btns = ttk.Frame(poster_inputs)
        pr_btns.pack(fill='x')
        ttk.Button(pr_btns, text="Resolve", width=8, command=lambda: self._resolve_into(pr_entry)).pack(side='left', padx=(0, 4))
        ttk.Button(pr_btns, text="📁 Browse", width=10, command=lambda: self._browse_image(pr_entry)).pack(side='left')

        vid_row = poster_row + 1
        ttk.Label(f, text="Video Embed:").grid(row=vid_row, column=0, sticky='w', padx=PX, pady=PY)
        vid_w = ttk.Entry(f, width=60)
        vid_w.grid(row=vid_row, column=1, columnspan=3, sticky='ew', padx=4, pady=PY)
        self.edit_widgets["videoEmbed"] = vid_w

        aud_row = vid_row + 1
        ttk.Label(f, text="Audio Tracks:", font=('', 10, 'bold')).grid(row=aud_row, column=0, sticky='w', padx=PX, pady=4)
        aud_row += 1
        af = ttk.Frame(f)
        af.grid(row=aud_row, column=0, columnspan=6, sticky='ew', padx=PX, pady=2)
        self.audio_listbox = tk.Listbox(af, height=4, width=40)
        self.audio_listbox.pack(side='left', fill='x', expand=True)
        abf = ttk.Frame(af)
        abf.pack(side='right', padx=4)
        ttk.Button(abf, text="+ Add MP3", width=10, command=self._browse_audio).pack(pady=2)
        ttk.Button(abf, text="− Remove", width=10, command=self._remove_audio_track).pack(pady=2)
        ttk.Button(abf, text="↑", width=10, command=lambda: self._move_audio_track(-1)).pack(pady=2)
        ttk.Button(abf, text="↓", width=10, command=lambda: self._move_audio_track(1)).pack(pady=2)
        aud_row += 1
        tnf = ttk.Frame(f)
        tnf.grid(row=aud_row, column=0, columnspan=6, sticky='ew', padx=PX, pady=2)
        ttk.Label(tnf, text="Track name:").pack(side='left')
        self.ent_track_name = ttk.Entry(tnf, width=30)
        self.ent_track_name.pack(side='left', padx=8, fill='x', expand=True)
        ttk.Button(tnf, text="Set Name", width=10, command=self._set_track_name).pack(side='left')
        self.audio_listbox.bind('<<ListboxSelect>>', self._on_audio_select)
        self._audio_names = []

        tech_row = aud_row + 1
        ttk.Label(f, text="Tech Stack:").grid(row=tech_row, column=0, sticky='w', padx=PX, pady=PY)
        self.ent_tech = ttk.Entry(f, width=60)
        self.ent_tech.grid(row=tech_row, column=1, columnspan=3, sticky='ew', padx=4, pady=PY)
        tech_row += 1
        ttk.Label(f, text="(Pro Tools, FMOD, Wwise, Reaper, iZotope)", foreground='gray').grid(row=tech_row, column=1, sticky='w', padx=4)

        rt_row = tech_row + 1
        ttk.Label(f, text="Roles:").grid(row=rt_row, column=0, sticky='nw', padx=PX, pady=PY)
        roles_frame = ttk.Frame(f)
        roles_frame.grid(row=rt_row, column=1, columnspan=3, sticky='w', padx=4, pady=PY)
        self.role_vars = {}
        role_filter = next((fd for fd in self.content["config"]["filters"] if fd["key"] == "role"), None)
        if role_filter:
            for i, opt in enumerate(role_filter["options"]):
                var = tk.BooleanVar()
                cb = ttk.Checkbutton(roles_frame, text=opt["label"], variable=var)
                cb.pack(side='left', padx=(0, 15))
                self.role_vars[opt["value"]] = var
                var.trace_add('write', lambda *a: self._mark_project_dirty())

        tags_row = rt_row + 1
        ttk.Label(f, text="Tags:").grid(row=tags_row, column=0, sticky='w', padx=PX, pady=PY)
        self.ent_tags = ttk.Entry(f, width=60)
        self.ent_tags.grid(row=tags_row, column=1, columnspan=3, sticky='ew', padx=4, pady=PY)

        toggle_row = tags_row + 1
        self.toggle_btn = ttk.Button(f, text="+ Extended Info & Gallery", command=self._toggle_extended)
        self.toggle_btn.grid(row=toggle_row, column=0, columnspan=6, sticky='w', padx=PX, pady=(15, 5))

        ext_row = toggle_row + 1
        self.extended_frame = ttk.Frame(f)
        self.extended_frame.grid(row=ext_row, column=0, columnspan=6, sticky='ew', padx=PX, pady=5)
        self.extended_frame.grid_remove() 

        ttk.Label(self.extended_frame, text="Extended Description (Role-focused CV text):", font=('', 10, 'bold')).grid(row=0, column=0, sticky='nw', padx=0, pady=PY)
        self.txt_extended_desc = tk.Text(self.extended_frame, width=60, height=6)
        self.txt_extended_desc.grid(row=1, column=0, sticky='ew', padx=0, pady=PY)

        ttk.Label(self.extended_frame, text="Gallery Images (Carousel):", font=('', 10, 'bold')).grid(row=2, column=0, sticky='nw', padx=0, pady=(10, PY))
        gal_frame = ttk.Frame(self.extended_frame)
        gal_frame.grid(row=3, column=0, sticky='ew')
        self.gallery_listbox = tk.Listbox(gal_frame, height=5, width=40)
        self.gallery_listbox.pack(side='left', fill='x', expand=True)
        gbf = ttk.Frame(gal_frame)
        gbf.pack(side='left', padx=4)
        ttk.Button(gbf, text="+ Add Image", width=10, command=self._browse_gallery_image).pack(pady=2)
        ttk.Button(gbf, text="− Remove", width=10, command=self._remove_gallery_image).pack(pady=2)
        ttk.Button(gbf, text="↑", width=10, command=lambda: self._move_gallery_image(-1)).pack(pady=2)
        ttk.Button(gbf, text="↓", width=10, command=lambda: self._move_gallery_image(1)).pack(pady=2)
        self.gallery_preview_label = ttk.Label(gal_frame, text='No preview', relief='solid', anchor='center', width=20)
        self.gallery_preview_label.pack(side='right', padx=(10, 0))
        self.gallery_listbox.bind('<<ListboxSelect>>', self._on_gallery_select)
        self._gallery_images = []

        save_row = ext_row + 1
        ttk.Button(f, text="💾 Save This Project", command=lambda: self._save_current_project()).grid(row=save_row, column=0, columnspan=6, pady=20)

    def _toggle_extended(self):
        if self.extended_frame.winfo_ismapped():
            self.extended_frame.grid_remove()
            self.toggle_btn.config(text="+ Extended Info & Gallery")
            self.edit_frame.update_idletasks()
            self.edit_canvas.yview_moveto(0.0)
        else:
            self.extended_frame.grid()
            self.toggle_btn.config(text="- Hide Extended Info & Gallery")
            self.edit_frame.update_idletasks()
            self.edit_canvas.yview_moveto(1.0)

    def _on_gallery_select(self, event):
        sel = self.gallery_listbox.curselection()
        if sel:
            idx = sel[0]
            if idx < len(self._gallery_images):
                rel_path = self._gallery_images[idx]
                self._update_gallery_preview(rel_path)

    def _remove_gallery_image(self):
        sel = self.gallery_listbox.curselection()
        if sel:
            idx = sel[0]
            self.gallery_listbox.delete(idx)
            if idx < len(self._gallery_images): del self._gallery_images[idx]
            self._mark_project_dirty()
            self.gallery_preview_label.config(image='', text='No preview')

    def _move_gallery_image(self, direction):
        sel = self.gallery_listbox.curselection()
        if not sel: return
        i = sel[0]
        j = i + direction
        if j < 0 or j >= self.gallery_listbox.size(): return
        items = list(self.gallery_listbox.get(0, 'end'))
        items[i], items[j] = items[j], items[i]
        self.gallery_listbox.delete(0, 'end')
        for item in items: self.gallery_listbox.insert('end', item)
        if i < len(self._gallery_images) and j < len(self._gallery_images):
            self._gallery_images[i], self._gallery_images[j] = self._gallery_images[j], self._gallery_images[i]
        self.gallery_listbox.selection_set(j)
        self._update_gallery_preview(self._gallery_images[j])
        self._mark_project_dirty()

    def _on_audio_select(self, event):
        sel = self.audio_listbox.curselection()
        if sel and sel[0] < len(self._audio_names):
            self.ent_track_name.delete(0, 'end')
            self.ent_track_name.insert(0, self._audio_names[sel[0]])

    def _set_track_name(self):
        sel = self.audio_listbox.curselection()
        if sel and sel[0] < len(self._audio_names):
            self._audio_names[sel[0]] = self.ent_track_name.get().strip()
            self._mark_project_dirty()

    def _remove_audio_track(self):
        sel = self.audio_listbox.curselection()
        if sel:
            idx = sel[0]
            self.audio_listbox.delete(idx)
            if idx < len(self._audio_names): del self._audio_names[idx]
            self._mark_project_dirty()

    def _move_audio_track(self, direction):
        sel = self.audio_listbox.curselection()
        if not sel: return
        i = sel[0]
        j = i + direction
        if j < 0 or j >= self.audio_listbox.size(): return
        items = list(self.audio_listbox.get(0, 'end'))
        items[i], items[j] = items[j], items[i]
        self.audio_listbox.delete(0, 'end')
        for item in items: self.audio_listbox.insert('end', item)
        if i < len(self._audio_names) and j < len(self._audio_names):
            self._audio_names[i], self._audio_names[j] = self._audio_names[j], self._audio_names[i]
        self.audio_listbox.selection_set(j)
        self._mark_project_dirty()

    def _on_project_select(self, event):
        sel = self.project_listbox.curselection()
        if not sel: return
        if self.project_dirty and self.current_project_index is not None:
            self._save_current_project(silent=True)
        
        list_idx = sel[0]
        real_idx = self.project_list_mapping[list_idx]
        self.current_project_index = real_idx
        self._load_project_to_form(real_idx)

    def _load_project_to_form(self, idx):
        p = self.content["projects"][idx]
        for k, w in self.edit_widgets.items():
            if isinstance(w, (ttk.Combobox, ttk.Entry)):
                w.delete(0, 'end')
                w.insert(0, p.get(k, ""))
            elif isinstance(w, tk.Text):
                w.delete('1.0', 'end')
                w.insert('1.0', p.get(k, ""))
        current_roles = p.get("roles", [])
        for role_key, var in self.role_vars.items():
            var.set(role_key in current_roles)
        self.ent_tags.delete(0, 'end')
        self.ent_tags.insert(0, ", ".join(p.get("tags", [])))
        self.ent_tech.delete(0, 'end')
        self.ent_tech.insert(0, ", ".join(p.get("techStack", [])))
        self.var_visible.set(p.get("visible", True))
        self.var_pinned.set(p.get("pinned", False))
        self.var_upcoming.set(p.get("upcoming", False))
        
        self.txt_extended_desc.delete('1.0', 'end')
        self.txt_extended_desc.insert('1.0', p.get("extendedDescription", ""))
        
        self.audio_listbox.delete(0, 'end')
        self._audio_names = []
        for track in p.get("audioTracks", []):
            url = track.get("url", "") if isinstance(track, dict) else str(track)
            name = track.get("name", "") if isinstance(track, dict) else ""
            self.audio_listbox.insert('end', url)
            self._audio_names.append(name)
        self.ent_track_name.delete(0, 'end')
        
        self.gallery_listbox.delete(0, 'end')
        self._gallery_images = []
        for img in p.get("galleryImages", []):
            self.gallery_listbox.insert('end', img)
            self._gallery_images.append(img)
            
        self.gallery_preview_label.config(image='', text='No preview')
        if self._gallery_images:
            self.gallery_listbox.selection_set(0)
            self._update_gallery_preview(self._gallery_images[0])

        self._update_thumbnail(p.get("poster", ""))
        
        self.extended_frame.grid_remove()
        self.toggle_btn.config(text="+ Extended Info & Gallery")
        self.edit_frame.update_idletasks()
        self.edit_canvas.yview_moveto(0.0)

        self.project_dirty = False
        self._update_title()
        self._bind_project_widgets_dirty()

    def _save_current_project(self, silent=False):
        if self.current_project_index is None:
            if not silent: messagebox.showwarning("No Selection", "Select a project or click '+ New Project'.")
            return
        p = self.content["projects"][self.current_project_index]
        sel = self.audio_listbox.curselection()
        if sel and sel[0] < len(self._audio_names):
            self._audio_names[sel[0]] = self.ent_track_name.get().strip()
        for k, w in self.edit_widgets.items():
            if isinstance(w, (ttk.Combobox, ttk.Entry)): p[k] = w.get().strip()
            elif isinstance(w, tk.Text): p[k] = w.get('1.0', 'end').strip()
        p["roles"] = [k for k, v in self.role_vars.items() if v.get()]
        p["tags"] = [t.strip() for t in self.ent_tags.get().split(",") if t.strip()]
        p["techStack"] = [t.strip() for t in self.ent_tech.get().split(",") if t.strip()]
        p["visible"] = self.var_visible.get()
        p["pinned"] = self.var_pinned.get()
        p["upcoming"] = self.var_upcoming.get()
        p["extendedDescription"] = self.txt_extended_desc.get('1.0', 'end').strip()
        
        tracks = []
        for i in range(self.audio_listbox.size()):
            url = self.audio_listbox.get(i)
            name = self._audio_names[i] if i < len(self._audio_names) else ""
            tracks.append({"url": url, "name": name})
        p["audioTracks"] = tracks
        
        p["galleryImages"] = list(self._gallery_images)

        save_content(self.content)
        self._refresh_project_list()
        for i, real_idx in enumerate(self.project_list_mapping):
            if real_idx == self.current_project_index:
                self.project_listbox.selection_set(i)
                break
        self.project_dirty = False
        self._update_title()

    def _new_project(self):
        if self.project_dirty and self.current_project_index is not None:
            self._save_current_project(silent=True)
        new = {
            "title": "New Project", "category": "film", "studio": "freelance",
            "studioLabel": "Independent", "year": "", "meta": "", "description": "",
            "poster": "", "referenceLink": "", "referenceLinkText": "View Project Reference",
            "roles": [], "tags": [], "techStack": [],
            "visible": True, "videoEmbed": "", "upcoming": False, "pinned": False,
            "audioTracks": [], "extendedDescription": "", "galleryImages": []
        }
        self.content["projects"].append(new)
        save_content(self.content)
        self._refresh_project_list()
        idx = len(self.content["projects"]) - 1
        self.current_project_index = idx
        for i, real_idx in enumerate(self.project_list_mapping):
            if real_idx == idx:
                self.project_listbox.selection_clear(0, 'end')
                self.project_listbox.selection_set(i)
                self.project_listbox.see(i)
                break
        self._load_project_to_form(idx)

    def _duplicate_project(self):
        if self.current_project_index is None:
            messagebox.showwarning("No Selection", "Select a project first.")
            return
        import copy
        dup = copy.deepcopy(self.content["projects"][self.current_project_index])
        dup["title"] += " (Copy)"
        dup["pinned"] = False
        self.content["projects"].insert(self.current_project_index + 1, dup)
        save_content(self.content)
        self._refresh_project_list()

    def _delete_project(self):
        if self.current_project_index is None: return
        title = self.content["projects"][self.current_project_index].get("title", "")
        if messagebox.askyesno("Confirm Delete", f"Delete '{title}'?"):
            del self.content["projects"][self.current_project_index]
            save_content(self.content)
            self.current_project_index = None
            self.project_dirty = False
            self._update_title()
            self._refresh_project_list()
            self._build_edit_form()

    def _move_project(self, direction):
        if self.current_project_index is None: return
        i = self.current_project_index
        j = i + direction
        if j < 0 or j >= len(self.content["projects"]): return
        self.content["projects"][i], self.content["projects"][j] = self.content["projects"][j], self.content["projects"][i]
        self.current_project_index = j
        save_content(self.content)
        self._refresh_project_list()
        for idx, real_idx in enumerate(self.project_list_mapping):
            if real_idx == j:
                self.project_listbox.selection_clear(0, 'end')
                self.project_listbox.selection_set(idx)
                self.project_listbox.see(idx)
                break

    def _build_filters_tab(self):
        main_frame = ttk.Frame(self.filters_tab)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        selector_frame = ttk.Frame(main_frame)
        selector_frame.pack(fill='x', pady=(0, 15))
        ttk.Label(selector_frame, text="Edit Filter:", font=('', 12, 'bold')).pack(side='left', padx=(0, 10))

        self.filter_selector_var = tk.StringVar()
        self.filter_selector = ttk.Combobox(selector_frame, textvariable=self.filter_selector_var, state="readonly", width=20)
        self.filter_selector.pack(side='left')
        self.filter_selector.bind("<<ComboboxSelected>>", self._on_filter_category_changed)

        filter_labels = [f["label"] for f in self.content["config"]["filters"]]
        self.filter_selector['values'] = filter_labels
        if filter_labels:
            self.filter_selector.current(0)

        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill='both', expand=True)

        list_frame = ttk.Frame(content_frame)
        list_frame.pack(side='left', fill='both', expand=True, padx=(0, 20))
        ttk.Label(list_frame, text="Options:", font=('', 11, 'bold')).pack(anchor='w', pady=(0, 5))

        self.filter_listbox = tk.Listbox(list_frame, font=('', 11), exportselection=False)
        self.filter_listbox.pack(side='left', fill='both', expand=True)
        self.filter_listbox.bind('<<ListboxSelect>>', self._on_filter_option_select)

        sb = ttk.Scrollbar(list_frame, orient='vertical', command=self.filter_listbox.yview)
        sb.pack(side='right', fill='y')
        self.filter_listbox.config(yscrollcommand=sb.set)

        ctrl_frame = ttk.LabelFrame(content_frame, text="Option Details", padding=15)
        ctrl_frame.pack(side='right', fill='y', padx=(20, 0))

        ttk.Label(ctrl_frame, text="Value (key):").grid(row=0, column=0, sticky='w', pady=5)
        self.filter_val_ent = ttk.Entry(ctrl_frame, width=30)
        self.filter_val_ent.grid(row=0, column=1, pady=5, padx=(10, 0))

        ttk.Label(ctrl_frame, text="Label (display):").grid(row=1, column=0, sticky='w', pady=5)
        self.filter_lbl_ent = ttk.Entry(ctrl_frame, width=30)
        self.filter_lbl_ent.grid(row=1, column=1, pady=5, padx=(10, 0))

        ttk.Label(ctrl_frame, text="Tooltip (optional):").grid(row=2, column=0, sticky='w', pady=5)
        self.filter_tip_ent = ttk.Entry(ctrl_frame, width=30)
        self.filter_tip_ent.grid(row=2, column=1, pady=5, padx=(10, 0))

        btn_frame = ttk.Frame(ctrl_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text="➕ Add New", width=15, command=self._add_filter_opt).pack(pady=3)
        ttk.Button(btn_frame, text="✏️ Update Selected", width=15, command=self._update_filter_opt).pack(pady=3)
        ttk.Button(btn_frame, text="🗑️ Delete Selected", width=15, command=self._delete_filter_opt).pack(pady=3)

        self._on_filter_category_changed()

    def _get_current_filter_def(self):
        label = self.filter_selector_var.get()
        for fdef in self.content["config"]["filters"]:
            if fdef["label"] == label:
                return fdef
        return None

    def _on_filter_category_changed(self, event=None):
        fdef = self._get_current_filter_def()
        if not fdef: return
        self.filter_listbox.delete(0, 'end')
        for opt in fdef["options"]:
            tip = opt.get("tooltip", "")
            tip_str = f" [Tooltip: {tip}]" if tip else ""
            self.filter_listbox.insert('end', f"{opt['value']} → {opt['label']}{tip_str}")
        self.filter_val_ent.delete(0, 'end')
        self.filter_lbl_ent.delete(0, 'end')
        self.filter_tip_ent.delete(0, 'end')

    def _on_filter_option_select(self, event):
        sel = self.filter_listbox.curselection()
        if not sel: return
        fdef = self._get_current_filter_def()
        if not fdef: return
        opt = fdef["options"][sel[0]]
        self.filter_val_ent.delete(0, 'end')
        self.filter_val_ent.insert(0, opt.get("value", ""))
        self.filter_lbl_ent.delete(0, 'end')
        self.filter_lbl_ent.insert(0, opt.get("label", ""))
        self.filter_tip_ent.delete(0, 'end')
        self.filter_tip_ent.insert(0, opt.get("tooltip", ""))

    def _add_filter_opt(self):
        fdef = self._get_current_filter_def()
        if not fdef: return
        val = self.filter_val_ent.get().strip()
        lbl = self.filter_lbl_ent.get().strip()
        tip = self.filter_tip_ent.get().strip()
        if not val or not lbl:
            messagebox.showwarning("Missing Info", "Value and Label are required.")
            return
        new_opt = {"value": val, "label": lbl}
        if tip: new_opt["tooltip"] = tip
        fdef["options"].append(new_opt)
        save_content(self.content)
        self._on_filter_category_changed()
        self.filter_val_ent.delete(0, 'end')
        self.filter_lbl_ent.delete(0, 'end')
        self.filter_tip_ent.delete(0, 'end')

    def _update_filter_opt(self):
        fdef = self._get_current_filter_def()
        if not fdef: return
        sel = self.filter_listbox.curselection()
        if not sel:
            messagebox.showinfo("Info", "Select an option to update.")
            return
        val = self.filter_val_ent.get().strip()
        lbl = self.filter_lbl_ent.get().strip()
        tip = self.filter_tip_ent.get().strip()
        if not val or not lbl: return
        updated_opt = {"value": val, "label": lbl}
        if tip: updated_opt["tooltip"] = tip
        fdef["options"][sel[0]] = updated_opt
        save_content(self.content)
        self._on_filter_category_changed()
        self.filter_listbox.selection_set(sel[0])

    def _delete_filter_opt(self):
        fdef = self._get_current_filter_def()
        if not fdef: return
        sel = self.filter_listbox.curselection()
        if not sel: return
        del fdef["options"][sel[0]]
        save_content(self.content)
        self._on_filter_category_changed()

    def _build_report_tab(self):
        main_frame = ttk.Frame(self.report_tab)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        stats_frame = ttk.LabelFrame(main_frame, text="Portfolio Overview", padding=15)
        stats_frame.pack(fill='x', pady=(0, 20))
        self.stats_grid_frame = ttk.Frame(stats_frame)
        self.stats_grid_frame.pack(fill='x')

        validator_frame = ttk.LabelFrame(main_frame, text="Data Health Validator", padding=15)
        validator_frame.pack(fill='both', expand=True)

        btn_frame = ttk.Frame(validator_frame)
        btn_frame.pack(fill='x', pady=(0, 10))
        ttk.Button(btn_frame, text="Run Validation", command=self._run_validation).pack(side='left')
        self.validator_status_label = ttk.Label(btn_frame, text="", foreground='gray')
        self.validator_status_label.pack(side='left', padx=20)

        columns = ("project", "category", "issue")
        self.validator_tree = ttk.Treeview(validator_frame, columns=columns, show="headings", height=12)
        self.validator_tree.heading("project", text="Project")
        self.validator_tree.heading("category", text="Category")
        self.validator_tree.heading("issue", text="Issue")
        
        self.validator_tree.column("project", width=200)
        self.validator_tree.column("category", width=80)
        self.validator_tree.column("issue", width=300)

        vsb = ttk.Scrollbar(validator_frame, orient="vertical", command=self.validator_tree.yview)
        self.validator_tree.configure(yscrollcommand=vsb.set)

        self.validator_tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        self._refresh_report()
        self._run_validation()

    def _refresh_report(self):
        for w in self.stats_grid_frame.winfo_children(): w.destroy()
        projects = self.content.get("projects", [])
        total = len(projects)
        visible = sum(1 for p in projects if p.get("visible", True))
        hidden = total - visible
        upcoming = sum(1 for p in projects if p.get("upcoming", False))
        pinned = sum(1 for p in projects if p.get("pinned", False))
        with_video = sum(1 for p in projects if p.get("videoEmbed", "").strip())
        with_audio = sum(1 for p in projects if len(p.get("audioTracks", [])) > 0)
        freelance = sum(1 for p in projects if p.get("studio", "") == "freelance")
        other = total - freelance

        stats = [
            ("Total Projects", total, "📊"), ("Visible", visible, "✅"), ("Hidden", hidden, "⏸️"),
            ("Upcoming", upcoming, "🚀"), ("Pinned", pinned, "⭐"), ("With Video", with_video, "🎬"),
            ("With Audio", with_audio, "🎵"), ("Freelance", freelance, "💼"), ("Studio Work", other, "🏢"),
        ]
        for i, (label, value, icon) in enumerate(stats):
            row = i // 3
            col = i % 3
            frame = ttk.Frame(self.stats_grid_frame, relief='ridge', borderwidth=1)
            frame.grid(row=row, column=col, sticky='nsew', padx=5, pady=5, ipadx=10, ipady=10)
            ttk.Label(frame, text=f"{icon} {value}", font=('', 20, 'bold')).pack(anchor='w')
            ttk.Label(frame, text=label, font=('', 10)).pack(anchor='w')

        for i in range(3):
            self.stats_grid_frame.columnconfigure(i, weight=1)

    def _run_validation(self):
        for item in self.validator_tree.get_children():
            self.validator_tree.delete(item)

        issues_found = 0
        for p in self.content["projects"]:
            title = p.get("title", "Untitled")
            cat = p.get("category", "").upper()
            if not p.get("poster", "").strip():
                self.validator_tree.insert("", "end", values=(title, cat, "Missing Poster Image"))
                issues_found += 1
            if not p.get("description", "").strip():
                self.validator_tree.insert("", "end", values=(title, cat, "Missing Description"))
                issues_found += 1
            if not p.get("referenceLink", "").strip():
                self.validator_tree.insert("", "end", values=(title, cat, "Missing Reference Link"))
                issues_found += 1

        if issues_found == 0:
            self.validator_tree.insert("", "end", values=("All Projects", "-", "✓ No issues found! Ready to publish."))
            self.validator_status_label.config(text="✓ Data is healthy", foreground="green")
        else:
            self.validator_status_label.config(text=f"⚠️ Found {issues_found} issues", foreground="orange")

def main():
    if not TEMPLATE_FILE.exists():
        print(f"ERROR: Template file not found at {TEMPLATE_FILE}")
        sys.exit(1)
    root = tk.Tk()
    app = PortfolioManagerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()