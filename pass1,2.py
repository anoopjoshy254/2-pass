import tkinter as tk
from tkinter import filedialog, messagebox, Text
from tkinter import ttk

class TwoPassAssembler:
    def __init__(self, display_intermediate, display_symtab, display_output):
        self.input_file_content = ''
        self.optab_file_content = ''
        self.opcode_list = []
        self.opcode_hex = {}
        self.sym_list = []
        self.sym_addresses = []
        self.locctr = 0
        self.starting_address = ''
        self.program_name = 'PROG'  # Default program name
        self.end_address = 0  # Track address of the END opcode
        self.program_length = 0  # Length of the program

        # Store Pass1 results for Pass2
        self.intermediate_lines = []
        self.symtab_lines = []

        # Callbacks for displaying results
        self.display_intermediate = display_intermediate
        self.display_symtab = display_symtab
        self.display_output = display_output

    def process_optab(self, content):
        lines = content.splitlines()
        for line in lines:
            words = line.strip().split()
            if len(words) == 2:
                opcode, hexcode = words
                self.opcode_list.append(opcode)
                self.opcode_hex[opcode] = hexcode

    def run_pass1(self):
        if not self.input_file_content:
            raise ValueError("Input file content is empty.")
        if not self.opcode_list:
            raise ValueError("Opcode table is empty.")

        lines = self.input_file_content.splitlines()
        self.intermediate_lines = []
        self.symtab_lines = ["Label\tLocctr\tFlag"]

        for line in lines:
            words = line.strip().split('\t')
            if len(words) <= 3:
                label = words[0].strip() if len(words) > 0 else ''
                opcode = words[1].strip() if len(words) > 1 else ''
                operand = words[2].strip() if len(words) > 2 else ''

                if opcode == 'START':
                    self.program_name = label if label else 'PROG'
                    self.locctr = int(operand, 16)
                    self.starting_address = hex(self.locctr)[2:].zfill(6).upper()
                    self.intermediate_lines.append(f"\t{label}\t{opcode}\t{operand}")
                else:
                    self.intermediate_lines.append(f"{hex(self.locctr)[2:].upper()}\t{label}\t{opcode}\t{operand}")
                    if label and label not in self.sym_list:
                        self.sym_list.append(label)
                        self.sym_addresses.append(self.locctr)
                        self.symtab_lines.append(f"{label}\t{hex(self.locctr)[2:].upper()}\t0")

                    if opcode in self.opcode_list:
                        self.locctr += 3
                    elif opcode == 'WORD':
                        self.locctr += 3
                    elif opcode == 'RESW':
                        self.locctr += 3 * int(operand)
                    elif opcode == 'RESB':
                        self.locctr += int(operand)
                    elif opcode == 'BYTE':
                        len_bytes = len(operand) - 3 if operand[0] in 'Cc' else (len(operand) - 3) // 2
                        self.locctr += len_bytes

        self.program_length = self.locctr - int(self.starting_address, 16)
        self.display_intermediate(self.intermediate_lines)
        self.display_symtab(self.symtab_lines)

    def run_pass2(self):
        if not self.intermediate_lines or not self.symtab_lines:
            raise ValueError("Pass 1 has not been executed. Please run Pass 1 first.")

        object_code_lines = []
        text_records = []
        current_text_record = ""
        text_record_start = ""
        text_record_length = 0

        for line in self.intermediate_lines:
            words = line.split('\t')
            address = words[0]
            label = words[1]
            opcode = words[2]
            operand = words[3] if len(words) > 3 else ''

            if opcode == 'END':
                self.end_address = self.locctr

            opcode_hex = self.opcode_hex.get(opcode, '')
            object_code = ''
            if opcode_hex:
                operand_address = '0000'
                if operand in self.sym_list:
                    sym_index = self.sym_list.index(operand)
                    operand_address = hex(self.sym_addresses[sym_index])[2:].zfill(4).upper()
                object_code = f"{opcode_hex}{operand_address}"
            elif opcode == 'WORD':
                object_code = hex(int(operand))[2:].zfill(6).upper()
            elif opcode == 'BYTE':
                if operand.startswith('C'):
                    # Convert characters to hex
                    chars = operand[2:-1]
                    object_code = ''.join([hex(ord(c))[2:].zfill(2).upper() for c in chars])
                elif operand.startswith('X'):
                    # Hex constant
                    object_code = operand[2:-1].upper()

            if object_code:
                # Manage Text Records
                if not current_text_record:
                    text_record_start = address
                if text_record_length + len(object_code) // 2 > 30:
                    # Flush current text record
                    text_records.append((text_record_start, text_record_length, current_text_record))
                    current_text_record = object_code
                    text_record_start = address
                    text_record_length = len(object_code) // 2
                else:
                    current_text_record += object_code
                    text_record_length += len(object_code) // 2

            # Append object code to the line
            object_code_lines.append(f"{line}\t{object_code}")

        # Flush the last text record
        if current_text_record:
            text_records.append((text_record_start, text_record_length, current_text_record))

        # Create Header, Text, and End records
        header_record = f"H^{self.program_name}^{self.starting_address}^{hex(self.program_length)[2:].upper()}"
        end_record = f"E^{self.starting_address}"

        text_record_strings = []
        for record in text_records:
            start, length, obj_code = record
            text_record_strings.append(f"T^{start}^{hex(length)[2:].upper()}^{obj_code}")

        # Combine all object code lines with Header, Text, and End
        full_object_code = [header_record] + text_record_strings + [end_record]

        # Prepare the Intermediate File with Object Codes
        intermediate_with_obj = []
        header = "Address\tLabel\tOpcode\tOperand\tObject Code"
        intermediate_with_obj.append(header)
        intermediate_with_obj.append("-" * len(header))
        intermediate_with_obj.extend(object_code_lines)

        # Append Object Program
        object_program = ["\nObject Program:", "-" * 15] + full_object_code

        # Combine both for display
        combined_output = intermediate_with_obj + object_program

        self.display_output(combined_output)


class AssemblerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pass 2 Assembler")
        self.assembler = TwoPassAssembler(
            self.display_intermediate,
            self.display_symtab,
            self.display_output
        )

        self.create_widgets()

    def create_widgets(self):
        # Main Border Frame
        border_frame = tk.Frame(self.root, bd=4, relief="groove", bg="#ffffff")
        border_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Configure grid layout for border_frame
        border_frame.columnconfigure(0, weight=1)
        border_frame.columnconfigure(1, weight=1)
        border_frame.rowconfigure(3, weight=1)

        # Style configuration
        style = ttk.Style()
        style.theme_use('clam')  # Use 'clam' theme for better appearance

        # Define custom styles
        style.configure("TButton",
                        font=('Helvetica', 10, 'bold'),
                        padding=6,
                        relief="raised",
                        foreground="white")
        style.map("TButton",
                  background=[('active', '#d1c4e9')])

        style.configure("Browse.TButton",
                        background="#009688")
        style.map("Browse.TButton",
                  background=[('active', '#00796b')])

        style.configure("Pass1.TButton",
                        background="#2196F3")
        style.map("Pass1.TButton",
                  background=[('active', '#1976D2')])

        style.configure("Pass2.TButton",
                        background="#FF9800")
        style.map("Pass2.TButton",
                  background=[('active', '#F57C00')])

        style.configure("Save.TButton",
                        background="#9C27B0")
        style.map("Save.TButton",
                  background=[('active', '#7B1FA2')])

        style.configure("TLabel",
                        font=('Helvetica', 10, 'bold'),
                        background="#ffffff",
                        foreground="#333333")

        style.configure("TFrame",
                        background="#ffffff")

        style.configure("TLabelFrame",
                        font=('Helvetica', 12, 'bold'),
                        foreground="#333333",
                        background="#f0f0f0",
                        borderwidth=2,
                        relief="groove")

        # File selection frame
        file_frame = ttk.Frame(border_frame, padding=10)
        file_frame.grid(row=0, column=0, columnspan=2, sticky='ew')

        # Optab File
        optab_label = ttk.Label(file_frame, text="Optab File:")
        optab_label.grid(row=0, column=0, pady=5, sticky='e')

        self.optab_file_entry = ttk.Entry(file_frame, width=50, font=('Helvetica', 10))
        self.optab_file_entry.grid(row=0, column=1, pady=5, padx=5)

        self.optab_browse_btn = ttk.Button(file_frame, text="Browse", command=self.load_optab_file, style="Browse.TButton")
        self.optab_browse_btn.grid(row=0, column=2, pady=5, padx=5)

        # Input File
        input_label = ttk.Label(file_frame, text="Input File:")
        input_label.grid(row=1, column=0, pady=5, sticky='e')

        self.input_file_entry = ttk.Entry(file_frame, width=50, font=('Helvetica', 10))
        self.input_file_entry.grid(row=1, column=1, pady=5, padx=5)

        self.input_browse_btn = ttk.Button(file_frame, text="Browse", command=self.load_input_file, style="Browse.TButton")
        self.input_browse_btn.grid(row=1, column=2, pady=5, padx=5)

        # Buttons Frame
        buttons_frame = ttk.Frame(border_frame, padding=10)
        buttons_frame.grid(row=2, column=0, columnspan=2, sticky='ew')

        # Pass1 Button
        self.pass1_btn = ttk.Button(buttons_frame, text="Run Pass 1", command=self.run_pass1, style="Pass1.TButton")
        self.pass1_btn.pack(side='left', padx=10)

        # Pass2 Button
        self.pass2_btn = ttk.Button(buttons_frame, text="Run Pass 2", command=self.run_pass2, style="Pass2.TButton")
        self.pass2_btn.pack(side='left', padx=10)

        # Disable Pass2 button initially
        self.pass2_btn.state(['disabled'])

        # Pass1 and Pass2 Frames
        pass1_frame = ttk.LabelFrame(border_frame, text="Pass 1", padding=10)
        pass1_frame.grid(row=3, column=0, padx=10, pady=5, sticky='nsew')

        pass2_frame = ttk.LabelFrame(border_frame, text="Pass 2", padding=10)
        pass2_frame.grid(row=3, column=1, padx=10, pady=5, sticky='nsew')

        # Configure grid weights for Pass1 and Pass2
        border_frame.columnconfigure(0, weight=1)
        border_frame.columnconfigure(1, weight=1)
        border_frame.rowconfigure(3, weight=1)

        # Pass1 Content
        # Intermediate File with Scrollbar
        intermediate_label = ttk.Label(pass1_frame, text="Intermediate File:")
        intermediate_label.grid(row=0, column=0, pady=(0,5), sticky='w')

        intermediate_frame = ttk.Frame(pass1_frame)
        intermediate_frame.grid(row=1, column=0, padx=5, pady=5, sticky='nsew')

        self.intermediate_text = tk.Text(intermediate_frame, height=15, width=60, bg="#e8f4f8", fg="#000000", font=('Arial', 10))
        self.intermediate_text.pack(side='left', fill='both', expand=True)

        intermediate_scroll = ttk.Scrollbar(intermediate_frame, command=self.intermediate_text.yview)
        intermediate_scroll.pack(side='right', fill='y')
        self.intermediate_text.configure(yscrollcommand=intermediate_scroll.set)

        # Symtab with Scrollbar
        symtab_label = ttk.Label(pass1_frame, text="Symtab:")
        symtab_label.grid(row=2, column=0, pady=(10,5), sticky='w')

        symtab_frame = ttk.Frame(pass1_frame)
        symtab_frame.grid(row=3, column=0, padx=5, pady=5, sticky='nsew')

        self.symtab_text = tk.Text(symtab_frame, height=15, width=60, bg="#e8f4f8", fg="#000000", font=('Arial', 10))
        self.symtab_text.pack(side='left', fill='both', expand=True)

        symtab_scroll = ttk.Scrollbar(symtab_frame, command=self.symtab_text.yview)
        symtab_scroll.pack(side='right', fill='y')
        self.symtab_text.configure(yscrollcommand=symtab_scroll.set)

        # Configure grid weights for pass1_frame
        pass1_frame.columnconfigure(0, weight=1)
        pass1_frame.rowconfigure(1, weight=1)
        pass1_frame.rowconfigure(3, weight=1)

        # Pass2 Content
        # Output File with Scrollbar
        output_label = ttk.Label(pass2_frame, text="Output File:")
        output_label.grid(row=0, column=0, pady=(0,5), sticky='w')

        output_frame = ttk.Frame(pass2_frame)
        output_frame.grid(row=1, column=0, padx=5, pady=5, sticky='nsew')

        self.output_text = tk.Text(output_frame, height=35, width=60, bg="#fff2e6", fg="#000000", font=('Arial', 10))
        self.output_text.pack(side='left', fill='both', expand=True)

        output_scroll = ttk.Scrollbar(output_frame, command=self.output_text.yview)
        output_scroll.pack(side='right', fill='y')
        self.output_text.configure(yscrollcommand=output_scroll.set)

        # Save Output Button
        self.save_output_btn = ttk.Button(pass2_frame, text="Save Output", command=self.save_output_file, style="Save.TButton")
        self.save_output_btn.grid(row=2, column=0, pady=10, sticky='e')

        # Status Bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = tk.Label(border_frame, textvariable=self.status_var, bd=1, relief='sunken', anchor='w', bg="#f0f0f0", font=('Helvetica', 10))
        status_bar.grid(row=4, column=0, columnspan=2, sticky='ew')

    def load_optab_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            try:
                with open(file_path, 'r') as file:
                    content = file.read()
                    self.optab_file_entry.delete(0, tk.END)
                    self.optab_file_entry.insert(0, file_path)
                    self.assembler.process_optab(content)
                self.status_var.set("Optab file loaded successfully.")
            except Exception as e:
                self.status_var.set(f"Failed to load Optab file: {e}")

    def load_input_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            try:
                with open(file_path, 'r') as file:
                    content = file.read()
                    self.input_file_entry.delete(0, tk.END)
                    self.input_file_entry.insert(0, file_path)
                    self.assembler.input_file_content = content
                self.status_var.set("Input file loaded successfully.")
            except Exception as e:
                self.status_var.set(f"Failed to load Input file: {e}")

    def run_pass1(self):
        try:
            self.assembler.run_pass1()
            self.status_var.set("Pass 1 completed successfully.")
            # Enable Pass2 button
            self.pass2_btn.state(['!disabled'])
        except Exception as e:
            self.status_var.set(f"Pass 1 failed: {e}")

    def run_pass2(self):
        try:
            self.assembler.run_pass2()
            self.status_var.set("Pass 2 completed successfully.")
        except Exception as e:
            self.status_var.set(f"Pass 2 failed: {e}")

    def save_output_file(self):
        output_content = self.output_text.get(1.0, tk.END).strip()
        if output_content:
            file_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                                     filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
            if file_path:
                try:
                    with open(file_path, 'w') as file:
                        file.write(output_content)
                    self.status_var.set("Output file saved successfully.")
                except Exception as e:
                    self.status_var.set(f"Failed to save Output file: {e}")
        else:
            self.status_var.set("No output to save.")

    def display_intermediate(self, lines):
        self.intermediate_text.delete(1.0, tk.END)
        header = "Address\tLabel\tOpcode\tOperand"
        self.intermediate_text.insert(tk.END, header + "\n")
        self.intermediate_text.insert(tk.END, "-" * 30 + "\n")
        self.intermediate_text.insert(tk.END, "\n".join(lines))

    def display_symtab(self, lines):
        self.symtab_text.delete(1.0, tk.END)
        header = "Label\tLocctr\tFlag"
        self.symtab_text.insert(tk.END, header + "\n")
        self.symtab_text.insert(tk.END, "-" * 20 + "\n")
        self.symtab_text.insert(tk.END, "\n".join(lines[1:]))  # Skip the initial header as it's added

    def display_output(self, lines):
        self.output_text.delete(1.0, tk.END)
        # Display Intermediate File with Object Codes
        intermediate_header = "Address\tLabel\tOpcode\tOperand\tObject Code"
        self.output_text.insert(tk.END, intermediate_header + "\n")
        self.output_text.insert(tk.END, "-" * len(intermediate_header) + "\n")
        for line in lines:
            if line.startswith("Object Program:"):
                self.output_text.insert(tk.END, line + "\n")
            elif line.startswith("H^") or line.startswith("T^") or line.startswith("E^"):
                self.output_text.insert(tk.END, line + "\n")
            else:
                self.output_text.insert(tk.END, line + "\n")


if __name__ == "__main__":
    root = tk.Tk()
    app = AssemblerApp(root)
    root.geometry("1400x900")  # Set a default window size
    root.configure(bg="#ffffff")  # Set background color for the window
    root.mainloop()
