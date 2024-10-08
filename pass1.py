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

    def process_input_file(self, content):
        lines = content.splitlines()
        intermediate_lines = []
        symtab_lines = ["Label\tLocctr\tFlag"]
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
                    intermediate_lines.append(f"\t{label}\t{opcode}\t{operand}")
                else:
                    intermediate_lines.append(f"{hex(self.locctr)[2:].upper()}\t{label}\t{opcode}\t{operand}")
                    if label and label not in self.sym_list:
                        self.sym_list.append(label)
                        self.sym_addresses.append(self.locctr)
                        symtab_lines.append(f"{label}\t{hex(self.locctr)[2:].upper()}\t0")

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

        self.display_intermediate(intermediate_lines)
        self.display_symtab(symtab_lines)
        self.pass_two(intermediate_lines)

    def pass_two(self, intermediate_lines):
        object_code_lines = []
        text_records = []
        current_text_record = ""
        text_record_start = ""
        text_record_length = 0

        program_length = self.locctr - int(self.starting_address, 16)

        for line in intermediate_lines:
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
        header_record = f"H^{self.program_name}^{self.starting_address}^{hex(program_length)[2:].upper()}"
        end_record = f"E^{self.starting_address}"

        text_record_strings = [header_record]
        for record in text_records:
            start, length, obj_code = record
            text_record_strings.append(f"T^{start}^{hex(length)[2:].upper()}^{obj_code}")
        text_record_strings.append(end_record)

        # Combine all object code lines with Header, Text, and End
        full_object_code = object_code_lines.copy()
        # Insert Header at the beginning
        full_object_code.insert(0, header_record)
        # Append Text records
        full_object_code.extend(text_record_strings[1:-1])  # Skip header and end
        # Append End record
        full_object_code.append(end_record)

        self.display_output(full_object_code)


class AssemblerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Two-Pass Assembler")
        self.assembler = TwoPassAssembler(
            self.display_intermediate,
            self.display_symtab,
            self.display_output
        )

        self.create_widgets()

    def create_widgets(self):
        # Configure grid layout for root
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(3, weight=1)
        self.root.rowconfigure(4, weight=1)

        # Style configuration
        style = ttk.Style()
        style.configure("TButton", padding=6, relief="flat",
                        background="#4CAF50", foreground="white", font=('Helvetica', 10, 'bold'))
        style.map("TButton",
                  background=[('active', '#45a049')])

        # File selection frame
        file_frame = tk.Frame(self.root, padx=10, pady=10)
        file_frame.grid(row=0, column=0, columnspan=2, sticky='we')

        # Optab File
        tk.Label(file_frame, text="Optab File:", font=('Helvetica', 10, 'bold')).grid(row=0, column=0, pady=5, sticky='e')
        self.optab_file_entry = tk.Entry(file_frame, width=40)
        self.optab_file_entry.grid(row=0, column=1, pady=5, padx=5)
        self.optab_browse_btn = tk.Button(file_frame, text="Browse", command=self.load_optab_file, bg="red", fg="white", font=('Helvetica', 10, 'bold'))
        self.optab_browse_btn.grid(row=0, column=2, pady=5, padx=5)

        # Input File
        tk.Label(file_frame, text="Input File:", font=('Helvetica', 10, 'bold')).grid(row=1, column=0, pady=5, sticky='e')
        self.input_file_entry = tk.Entry(file_frame, width=40)
        self.input_file_entry.grid(row=1, column=1, pady=5, padx=5)
        self.input_browse_btn = tk.Button(file_frame, text="Browse", command=self.load_input_file, bg="#2196F3", fg="white", font=('Helvetica', 10, 'bold'))
        self.input_browse_btn.grid(row=1, column=2, pady=5, padx=5)

        # Convert Button
        self.convert_btn = tk.Button(self.root, text="Convert", command=self.process_files, bg="#4CAF50", fg="white", font=('Helvetica', 12, 'bold'))
        self.convert_btn.grid(row=2, column=0, columnspan=2, pady=10)

        # Pass1 and Pass2 Frames
        pass1_frame = tk.LabelFrame(self.root, text="Pass 1", padx=10, pady=10, font=('Helvetica', 12, 'bold'), fg="#333333", bg="#FFCCCB")  # Light red background
        pass1_frame.grid(row=3, column=0, sticky='nsew')

        pass2_frame = tk.LabelFrame(self.root, text="Pass 2", padx=10, pady=10, font=('Helvetica', 12, 'bold'), fg="#333333", bg="#ADD8E6")  # Light blue background
        pass2_frame.grid(row=3, column=1, sticky='nsew')

        # Intermediate File Text Area
        self.intermediate_text = Text(pass1_frame, wrap='word', width=50, height=20, bg="#FFFFFF", font=('Courier New', 10))
        self.intermediate_text.grid(row=0, column=0)
        self.intermediate_label = tk.Label(pass1_frame, text="Intermediate File", fg="red", bg="#FFCCCB", font=('Helvetica', 10, 'bold'))
        self.intermediate_label.grid(row=1, column=0)

        # Symbol Table Text Area
        self.symtab_text = Text(pass1_frame, wrap='word', width=50, height=20, bg="#FFFFFF", font=('Courier New', 10))
        self.symtab_text.grid(row=2, column=0)
        self.symtab_label = tk.Label(pass1_frame, text="Symtab", fg="blue", bg="#FFCCCB", font=('Helvetica', 10, 'bold'))
        self.symtab_label.grid(row=3, column=0)

        # Output File Text Area
        self.output_text = Text(pass2_frame, wrap='word', width=50, height=20, bg="#FFFFFF", font=('Courier New', 10))
        self.output_text.grid(row=0, column=0)
        self.output_label = tk.Label(pass2_frame, text="Output File", fg="green", bg="#ADD8E6", font=('Helvetica', 10, 'bold'))
        self.output_label.grid(row=1, column=0)

    def load_optab_file(self):
        optab_file = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if optab_file:
            with open(optab_file, 'r') as file:
                self.assembler.optab_file_content = file.read()
            self.assembler.process_optab(self.assembler.optab_file_content)
            self.optab_file_entry.delete(0, tk.END)
            self.optab_file_entry.insert(0, optab_file)
            messagebox.showinfo("Info", f"Optab file loaded: {optab_file}")

    def load_input_file(self):
        input_file = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if input_file:
            with open(input_file, 'r') as file:
                self.assembler.input_file_content = file.read()
            self.input_file_entry.delete(0, tk.END)
            self.input_file_entry.insert(0, input_file)
            messagebox.showinfo("Info", f"Input file loaded: {input_file}")

    def process_files(self):
        if not self.assembler.optab_file_content or not self.assembler.input_file_content:
            messagebox.showwarning("Warning", "Please load both Optab and Input files.")
            return
        self.assembler.process_input_file(self.assembler.input_file_content)

    def display_intermediate(self, lines):
        self.intermediate_text.delete(1.0, tk.END)
        for line in lines:
            self.intermediate_text.insert(tk.END, line + "\n")

    def display_symtab(self, lines):
        self.symtab_text.delete(1.0, tk.END)
        for line in lines:
            self.symtab_text.insert(tk.END, line + "\n")

    def display_output(self, lines):
        self.output_text.delete(1.0, tk.END)
        for line in lines:
            self.output_text.insert(tk.END, line + "\n")


if __name__ == "__main__":
    root = tk.Tk()
    app = AssemblerApp(root)
    root.mainloop()
