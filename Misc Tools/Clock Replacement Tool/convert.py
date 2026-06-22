import openpyxl

def excel_to_aligned_text(excel_filepath, txt_filepath, padding= 4):
    """
    Parses an Excel file and writes it to a text file with perfectly aligned columns.
    
    Args:
        excel_filepath (str): Path to the input .xlsx file.
        txt_filepath (str): Path to the output .txt file.
        padding (int): Number of extra spaces between columns.
    """
    try:
        # Load the workbook (data_only=True ensures we get formula results)
        wb = openpyxl.load_workbook(excel_filepath, data_only=True)
        sheet = wb.active
    except FileNotFoundError:
        print(f"Error: The file '{excel_filepath}' was not found.")
        return
    except Exception as e:
        print(f"An error occurred while loading the Excel file: {e}")
        return

    # Step 1: Read all data into a list of lists, converting to stripped strings
    data = []
    for row in sheet.iter_rows(values_only=True):
        row_data = [str(cell).strip() if cell is not None else "" for cell in row]
        
        # Only keep the row if it contains at least one non-empty value
        if any(row_data):
            data.append(row_data)

    if not data:
        print("The spreadsheet is empty or contains no readable data.")
        return

    # Step 2: Identify the bounds and remove columns between them
    header_row = data[0]
    start_idx = -1
    end_idx = -1

    # Locate the indices of the two target columns
    for i, header in enumerate(header_row):
        # Using 'in' allows for slight variations like "30-min rate " 
        if "30-min rate" in header:
            start_idx = i
        elif "1-day rate squared" in header:
            end_idx = i

    num_columns = len(header_row)
    
    # If both columns are found and in the expected order, filter the columns
    if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
        # Keep columns up to and including start_idx, and from end_idx onwards
        cols_to_keep = [i for i in range(num_columns) if i <= start_idx or i >= end_idx]
        
        # Rebuild the data using only the kept columns
        filtered_data = []
        for row in data:
            new_row = [row[i] for i in cols_to_keep if i < len(row)]
            filtered_data.append(new_row)
            
        data = filtered_data

    # Step 3: Determine the maximum string length for each remaining column
    num_columns = len(data[0])
    col_widths = [0] * num_columns

    for row in data:
        for i, cell_value in enumerate(row):
            if len(cell_value) > col_widths[i]:
                col_widths[i] = len(cell_value)

    # Step 4: Write to the text file using the calculated widths for alignment
    try:
        with open(txt_filepath, 'w', encoding='utf-8') as f:
            for row in data:
                formatted_row = ""
                for i, cell_value in enumerate(row):
                    target_width = col_widths[i] + padding
                    formatted_row += cell_value.ljust(target_width)
                
                f.write(formatted_row.rstrip() + '\n')
                
        print(f"Success! Aligned data has been written to '{txt_filepath}'")
        
    except Exception as e:
         print(f"An error occurred while writing the text file: {e}")

# ==========================================
# Example Usage
# ==========================================
if __name__ == "__main__":
    input_excel = '//noodle/fot/engineering/ccdm/Clock_Timing/Clock Rate Trending_files/Clock Rate Trending (Data Only).xlsx'
    output_text = 'C:/Users/RHoover/Desktop/clock_rate.txt'
    
    excel_to_aligned_text(input_excel, output_text, padding= 4)