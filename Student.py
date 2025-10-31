# Updated Student Management System
# - Explicit SELECT columns to avoid column-order mismatches
# - Optional modern look using ttkbootstrap if available
# - Responsive layout with PanedWindow and weight-configured grids
# - Fixed insert/update/search/export to map fields reliably
# - Smaller default window size and minimum size

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import re
from typing import Any, Dict, Tuple
from datetime import datetime
import csv

# Try to use ttkbootstrap for a modern UI if installed (optional)
try:
    import importlib
    tb = importlib.import_module('ttkbootstrap')
    try:
        constants_mod = importlib.import_module('ttkbootstrap.constants')
        # Import any uppercase constants into globals (if present)
        for _name in dir(constants_mod):
            if _name.isupper():
                globals()[_name] = getattr(constants_mod, _name)
    except Exception:
        # If constants module isn't available, continue without constants
        pass
    USE_BOOTSTRAP = True
except Exception:
    tb = None
    USE_BOOTSTRAP = False


class DatabaseManager:
    """Handles all database operations with explicit column ordering."""

    def __init__(self, db_name: str = 'management.db'):
        self.db_name = db_name
        self.connection = sqlite3.connect(self.db_name)
        self.initialize_database()
        self.update_schema()

    def initialize_database(self):
        cur = self.connection.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT,
                student_email TEXT,
                student_phone TEXT,
                student_college TEXT,
                student_department TEXT,
                student_year TEXT,
                student_address TEXT,
                student_city TEXT,
                student_state TEXT,
                student_pincode TEXT,
                date_added TEXT,
                last_modified TEXT
            )
        """)
        # Add simple unique indices for easy integrity messages
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_students_email ON students(student_email)")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_students_phone ON students(student_phone)")
        self.connection.commit()

    def update_schema(self):
        # Add missing columns defensively (keeps existing rows valid)
        cur = self.connection.cursor()
        cur.execute("PRAGMA table_info(students)")
        cols = [r[1] for r in cur.fetchall()]
        required = [
            ('student_id', 'INTEGER'), ('student_name', 'TEXT'), ('student_email', 'TEXT'),
            ('student_phone', 'TEXT'), ('student_college', 'TEXT'), ('student_department', 'TEXT'),
            ('student_year', 'TEXT'), ('student_address', 'TEXT'), ('student_city', 'TEXT'),
            ('student_state', 'TEXT'), ('student_pincode', 'TEXT'), ('date_added', 'TEXT'), ('last_modified', 'TEXT')
        ]
        for name, typ in required:
            if name not in cols:
                cur.execute(f"ALTER TABLE students ADD COLUMN {name} {typ}")
        self.connection.commit()

    def insert_student(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        cur = self.connection.cursor()
        try:
            cur.execute(
                """INSERT INTO students (
                    student_name, student_email, student_phone, student_college,
                    student_department, student_year, student_address, student_city,
                    student_state, student_pincode, date_added, last_modified
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    data['name'], data['email'], data['phone'], data['college'],
                    data['department'], data['year'], data['address'], data['city'],
                    data['state'], data['pincode'], data['date_added'], data['last_modified']
                )
            )
            self.connection.commit()
            return True, ''
        except sqlite3.IntegrityError as e:
            msg = str(e).lower()
            if 'email' in msg:
                return False, 'Email already exists.'
            if 'phone' in msg:
                return False, 'Phone already exists.'
            return False, 'Integrity error: ' + str(e)
        except Exception as e:
            return False, str(e)

    def get_all_students(self):
        # Explicit column ordering to ensure GUI mapping is stable
        cur = self.connection.cursor()
        cur.execute(
            """SELECT student_id, student_name, student_email, student_phone,
                      student_college, student_department, student_year, student_address,
                      student_city, student_state, student_pincode, date_added, last_modified
               FROM students ORDER BY student_id DESC"""
        )
        return cur.fetchall()

    def update_student(self, student_id: int, data: Dict[str, Any]) -> Tuple[bool, str]:
        cur = self.connection.cursor()
        try:
            cur.execute(
                """UPDATE students SET
                    student_name=?, student_email=?, student_phone=?, student_college=?,
                    student_department=?, student_year=?, student_address=?, student_city=?,
                    student_state=?, student_pincode=?, last_modified=? WHERE student_id=?""",
                (
                    data['name'], data['email'], data['phone'], data['college'],
                    data['department'], data['year'], data['address'], data['city'],
                    data['state'], data['pincode'], data['last_modified'], student_id
                )
            )
            self.connection.commit()
            if cur.rowcount == 0:
                return False, 'No row updated (ID may not exist).'
            return True, ''
        except sqlite3.IntegrityError as e:
            msg = str(e).lower()
            if 'email' in msg:
                return False, 'Email already exists.'
            if 'phone' in msg:
                return False, 'Phone already exists.'
            return False, str(e)
        except Exception as e:
            return False, str(e)

    def delete_student(self, student_id: int) -> Tuple[bool, str]:
        cur = self.connection.cursor()
        try:
            cur.execute("DELETE FROM students WHERE student_id=?", (student_id,))
            self.connection.commit()
            return True, ''
        except Exception as e:
            return False, str(e)

    def search_students(self, term: str):
        cur = self.connection.cursor()
        q = f"%{term}%"
        cur.execute(
            """SELECT student_id, student_name, student_email, student_phone,
                      student_college, student_department, student_year, student_address,
                      student_city, student_state, student_pincode, date_added, last_modified
               FROM students
               WHERE student_name LIKE ? OR student_email LIKE ? OR student_phone LIKE ?
                 OR student_college LIKE ? OR student_department LIKE ? OR student_city LIKE ?
               ORDER BY student_id DESC""",
            (q, q, q, q, q, q)
        )
        return cur.fetchall()

    def close(self):
        if self.connection:
            self.connection.close()


class InputValidator:
    @staticmethod
    def validate_name(name: str) -> Tuple[bool, str]:
        if not name.strip():
            return False, 'Name cannot be empty.'
        if len(name.strip()) < 2:
            return False, 'Name must be at least 2 characters.'
        if not re.match(r'^[\w\s.\-]+$', name):
            return False, 'Name contains invalid characters.'
        return True, ''

    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        if not email.strip():
            return False, 'Email cannot be empty.'
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return False, 'Invalid email format.'
        return True, ''

    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, str]:
        p = re.sub(r'[\s\-()]', '', phone)
        if not p.isdigit() or not (10 <= len(p) <= 15):
            return False, 'Phone must be 10-15 digits.'
        return True, ''

    @staticmethod
    def validate_pincode(pin: str) -> Tuple[bool, str]:
        if not pin.isdigit() or len(pin) not in (5, 6):
            return False, 'Pincode must be 5 or 6 digits.'
        return True, ''


class StudentManagementApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        title = "Student Management System"
        if USE_BOOTSTRAP:
            self.style = tb.Style('flatly')
            # tb.Tk() would create its own Tk instance; we keep using provided root
            self.root.title(title + ' - Modern')
        else:
            self.root.title(title)

        # Smaller default size and a minimum size
        self.root.geometry('1200x760')
        self.root.minsize(1000, 640)

        self.db = DatabaseManager()
        self.validator = InputValidator()

        self.setup_ui()
        self.load_students()

        self.root.protocol('WM_DELETE_WINDOW', self.on_closing)

    def setup_ui(self):
        # Header
        header = ttk.Frame(self.root)
        header.pack(fill=tk.X)
        lbl = ttk.Label(header, text='🎓 Student Management System', font=('Arial', 18, 'bold'))
        lbl.pack(padx=10, pady=8)

        # Split area: form on top, table underneath using PanedWindow for resize
        pw = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        pw.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        form_frame = ttk.Labelframe(pw, text='Student Information', padding=10)
        table_frame = ttk.Labelframe(pw, text='Student Records', padding=6)
        pw.add(form_frame, weight=1)
        pw.add(table_frame, weight=3)

        # Form layout using grid with three columns
        for c in range(3):
            form_frame.columnconfigure(c, weight=1)

        # Personal
        personal = ttk.Labelframe(form_frame, text='Personal', padding=8)
        personal.grid(row=0, column=0, sticky='nsew', padx=6, pady=4)
        ttk.Label(personal, text='Full Name:').grid(row=0, column=0, sticky='w')
        self.name = ttk.Entry(personal)
        self.name.grid(row=0, column=1, sticky='ew', padx=6, pady=4)
        ttk.Label(personal, text='Email:').grid(row=1, column=0, sticky='w')
        self.email = ttk.Entry(personal)
        self.email.grid(row=1, column=1, sticky='ew', padx=6, pady=4)
        ttk.Label(personal, text='Phone:').grid(row=2, column=0, sticky='w')
        self.phone = ttk.Entry(personal)
        self.phone.grid(row=2, column=1, sticky='ew', padx=6, pady=4)

        # Academic
        acad = ttk.Labelframe(form_frame, text='Academic', padding=8)
        acad.grid(row=0, column=1, sticky='nsew', padx=6, pady=4)
        ttk.Label(acad, text='College:').grid(row=0, column=0, sticky='w')
        self.college = ttk.Entry(acad)
        self.college.grid(row=0, column=1, sticky='ew', padx=6, pady=4)
        ttk.Label(acad, text='Department:').grid(row=1, column=0, sticky='w')
        self.department = ttk.Combobox(acad, values=[
            'Computer Science', 'Information Technology', 'Electronics', 'Mechanical', 'Civil', 'Electrical', 'Other'
        ])
        self.department.grid(row=1, column=1, sticky='ew', padx=6, pady=4)
        ttk.Label(acad, text='Year/Sem:').grid(row=2, column=0, sticky='w')
        self.year = ttk.Combobox(acad, values=['1st Year','2nd Year','3rd Year','4th Year'])
        self.year.grid(row=2, column=1, sticky='ew', padx=6, pady=4)

        # Address
        addr = ttk.Labelframe(form_frame, text='Address', padding=8)
        addr.grid(row=0, column=2, sticky='nsew', padx=6, pady=4)
        ttk.Label(addr, text='Street:').grid(row=0, column=0, sticky='w')
        self.address = ttk.Entry(addr)
        self.address.grid(row=0, column=1, sticky='ew', padx=6, pady=4)
        ttk.Label(addr, text='City:').grid(row=1, column=0, sticky='w')
        self.city = ttk.Entry(addr)
        self.city.grid(row=1, column=1, sticky='ew', padx=6, pady=4)
        ttk.Label(addr, text='State:').grid(row=2, column=0, sticky='w')
        self.state = ttk.Entry(addr)
        self.state.grid(row=2, column=1, sticky='ew', padx=6, pady=4)
        ttk.Label(addr, text='Pincode:').grid(row=3, column=0, sticky='w')
        self.pincode = ttk.Entry(addr)
        self.pincode.grid(row=3, column=1, sticky='ew', padx=6, pady=4)

        # Buttons
        btns = ttk.Frame(form_frame)
        btns.grid(row=1, column=0, columnspan=3, pady=8)
        ttk.Button(btns, text='Add', command=self.add_student).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text='Update', command=self.update_student).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text='Delete', command=self.delete_student).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text='Clear', command=self.clear_fields).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text='Export', command=self.export_data).pack(side=tk.LEFT, padx=6)

        # Search
        search_frame = ttk.Frame(form_frame)
        search_frame.grid(row=2, column=0, columnspan=3, sticky='ew', pady=(4,0))
        ttk.Label(search_frame, text='Search:').pack(side=tk.LEFT, padx=4)
        self.search = ttk.Entry(search_frame)
        self.search.pack(side=tk.LEFT, fill='x', expand=True, padx=6)
        self.search.bind('<KeyRelease>', lambda e: self.search_students())
        ttk.Button(search_frame, text='Show All', command=self.load_students).pack(side=tk.LEFT, padx=4)

        # Table
        cols = ("ID","Name","Email","Phone","College","Department","Year",
                "Address","City","State","Pincode","Date Added","Last Modified")
        self.tree = ttk.Treeview(table_frame, columns=cols, show='headings')
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=100, anchor='w')
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

    def get_form(self) -> Tuple[bool, Dict[str, Any]]:
        name = self.name.get().strip()
        email = self.email.get().strip()
        phone = re.sub(r'[\s\-()]', '', self.phone.get().strip())
        college = self.college.get().strip()
        department = self.department.get().strip()
        year = self.year.get().strip()
        address = self.address.get().strip()
        city = self.city.get().strip()
        state = self.state.get().strip()
        pincode = self.pincode.get().strip()

        ok, msg = InputValidator.validate_name(name)
        if not ok:
            messagebox.showerror('Validation', msg); self.name.focus(); return False, {}
        ok, msg = InputValidator.validate_email(email)
        if not ok:
            messagebox.showerror('Validation', msg); self.email.focus(); return False, {}
        ok, msg = InputValidator.validate_phone(phone)
        if not ok:
            messagebox.showerror('Validation', msg); self.phone.focus(); return False, {}
        ok, msg = InputValidator.validate_pincode(pincode)
        if not ok:
            messagebox.showerror('Validation', msg); self.pincode.focus(); return False, {}

        return True, {
            'name': name, 'email': email, 'phone': phone, 'college': college,
            'department': department, 'year': year, 'address': address,
            'city': city, 'state': state, 'pincode': pincode
        }

    def add_student(self):
        ok, data = self.get_form()
        if not ok: return
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data['date_added'] = now; data['last_modified'] = now
        success, err = self.db.insert_student(data)
        if success:
            messagebox.showinfo('Success', 'Student added')
            self.clear_fields(); self.load_students()
        else:
            messagebox.showerror('Error', err)

    def update_student(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('Select', 'Select a row to update'); return
        sid = self.tree.item(sel[0])['values'][0]
        ok, data = self.get_form()
        if not ok: return
        data['last_modified'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        success, err = self.db.update_student(sid, data)
        if success:
            messagebox.showinfo('Success', 'Updated')
            self.clear_fields(); self.load_students()
        else:
            messagebox.showerror('Error', err)

    def delete_student(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('Select', 'Select a row to delete'); return
        sid = self.tree.item(sel[0])['values'][0]
        if messagebox.askyesno('Confirm', 'Delete selected student?'):
            success, err = self.db.delete_student(sid)
            if success:
                messagebox.showinfo('Deleted', 'Student deleted')
                self.clear_fields(); self.load_students()
            else:
                messagebox.showerror('Error', err)

    def load_students(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        rows = self.db.get_all_students()
        for r in rows:
            self.tree.insert('', tk.END, values=r)

    def search_students(self):
        term = self.search.get().strip()
        if not term:
            self.load_students(); return
        for i in self.tree.get_children():
            self.tree.delete(i)
        rows = self.db.search_students(term)
        for r in rows:
            self.tree.insert('', tk.END, values=r)

    def on_select(self, event):
        sel = self.tree.selection()
        if not sel: return
        vals = self.tree.item(sel[0])['values']
        # Map values explicitly (remember ordering matches get_all_students)
        self.name.delete(0, tk.END); self.name.insert(0, vals[1])
        self.email.delete(0, tk.END); self.email.insert(0, vals[2])
        self.phone.delete(0, tk.END); self.phone.insert(0, vals[3])
        self.college.delete(0, tk.END); self.college.insert(0, vals[4])
        self.department.set(vals[5] or '')
        self.year.set(vals[6] or '')
        self.address.delete(0, tk.END); self.address.insert(0, vals[7])
        self.city.delete(0, tk.END); self.city.insert(0, vals[8])
        self.state.delete(0, tk.END); self.state.insert(0, vals[9])
        self.pincode.delete(0, tk.END); self.pincode.insert(0, vals[10])

    def clear_fields(self):
        for w in (self.name, self.email, self.phone, self.college, self.address, self.city, self.state, self.pincode, self.search):
            w.delete(0, tk.END)
        self.department.set(''); self.year.set('')

    def export_data(self):
        path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV','*.csv')])
        if not path: return
        rows = self.db.get_all_students()
        with open(path, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(["ID","Name","Email","Phone","College","Department","Year","Address","City","State","Pincode","Date Added","Last Modified"])
            w.writerows(rows)
        messagebox.showinfo('Export', f'Exported {len(rows)} rows')

    def on_closing(self):
        if messagebox.askokcancel('Quit', 'Quit application?'):
            self.db.close(); self.root.destroy()


def main():
    if USE_BOOTSTRAP:
        root = tb.Window(themename='flatly')
    else:
        root = tk.Tk()
    app = StudentManagementApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
