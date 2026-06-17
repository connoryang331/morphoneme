import csv
from pathlib import Path

TSV_PATH = Path(__file__).parent.parent / "data" / "morph_data.tsv"

def calculate_stats():
    if not TSV_PATH.exists():
        print(f"Error: {TSV_PATH} does not exist.")
        return

    high_count = 0
    medium_count = 0
    low_count = 0
    very_low_count = 0
    zero_count = 0
    null_count = 0
    total_count = 0

    print(f"Reading {TSV_PATH.name}...")
    with open(TSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        
        has_freq_col = len(header) >= 4 and header[3] == "Frequency"
        if not has_freq_col:
            print("Error: The TSV file does not have a 'Frequency' column as the 4th column.")
            return

        for row in reader:
            if not row:
                continue
            total_count += 1
            freq_str = row[3] if len(row) > 3 else ""
            
            if freq_str == "":
                # frequency IS NULL
                null_count += 1
            else:
                try:
                    freq = float(freq_str)
                    if freq >= 5.0:
                        high_count += 1
                    elif freq >= 1.0:
                        medium_count += 1
                    elif freq >= 0.1:
                        low_count += 1
                    elif freq > 0.0:
                        very_low_count += 1
                    elif freq == 0.0:
                        zero_count += 1
                    else:
                        zero_count += 1
                except ValueError:
                    null_count += 1

    print("\n" + "=" * 45)
    print(f"Frequency Statistics for {TSV_PATH.name}")
    print("=" * 45)
    print(f"{'Category':<12} | {'Condition':<20} | {'Count':<10} | {'Percentage':<10}")
    print("-" * 70)
    
    def format_row(name, cond, count):
        pct = (count / total_count * 100) if total_count > 0 else 0
        print(f"{name:<12} | {cond:<20} | {count:<10,} | {pct:>8.2f}%")

    format_row("high", "freq >= 5.0", high_count)
    format_row("medium", "1.0 <= freq < 5.0", medium_count)
    format_row("low", "0.1 <= freq < 1.0", low_count)
    format_row("very_low", "0.0 < freq < 0.1", very_low_count)
    format_row("zero", "freq == 0.0", zero_count)
    format_row("null", "freq IS NULL", null_count)
    
    print("-" * 70)
    print(f"{'Total':<12} | {'':<20} | {total_count:<10,} | {100.0:>8.2f}%")
    print("=" * 70)

if __name__ == "__main__":
    calculate_stats()
