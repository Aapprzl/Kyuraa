# name:        word-counter
# description: Menghitung jumlah kata dan karakter dalam teks
# version:     1.0
# author:      Kyuraa

def run(teks: str) -> str:
    """
    Menghitung jumlah kata dan karakter dalam teks.
    Args:
        teks (str): Teks yang ingin dihitung
    """
    if not teks:
        return "Teks kosong."
        
    words = len(teks.strip().split())
    chars = len(teks)
    sentences = teks.count('.') + teks.count('!') + teks.count('?')
    
    return (
        f"📊 Statistik Teks:\n"
        f"- Kata     : {words}\n"
        f"- Karakter : {chars}\n"
        f"- Kalimat  : {sentences or 1}"
    )
