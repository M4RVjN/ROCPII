"""
驗證演算法模組

本模組存放各種用於驗證特定個資格式正確性的函式，例如檢查碼演算法。
所有在此處的函式都應經過嚴格的單元測試，確保其準確無誤。
"""
import re
from typing import Optional

def is_valid_taiwan_id(id_str: Optional[str]) -> bool:
    """
    使用檢查碼演算法，驗證台灣身分證字號是否有效。

    Args:
        id_str: 待驗證的身分證字號字串。

    Returns:
        如果格式和檢查碼都正確，則回傳 True，否則回傳 False。
    """
    if not id_str or not isinstance(id_str, str):
        return False

    id_str = id_str.strip().upper()

    # 1. 驗證基本格式：1個大寫字母 + 9個數字
    if not re.match(r'^[A-Z][12]\d{8}$', id_str):
        return False

    # 2. 檢查碼演算法
    letter_map = {
        "A": 10, "B": 11, "C": 12, "D": 13, "E": 14, "F": 15, "G": 16, "H": 17,
        "I": 34, "J": 18, "K": 19, "L": 20, "M": 21, "N": 22, "O": 35, "P": 23,
        "Q": 24, "R": 25, "S": 26, "T": 27, "U": 28, "V": 29, "W": 32, "X": 30,
        "Y": 31, "Z": 33
    }

    # 將英文字母轉換為對應的二位數
    num_from_letter = letter_map.get(id_str[0])
    if num_from_letter is None:
        return False

    # 組合數字串
    all_digits = str(num_from_letter) + id_str[1:]

    # 加權總和
    weights = [1, 9, 8, 7, 6, 5, 4, 3, 2, 1, 1]
    weighted_sum = sum(int(digit) * weight for digit, weight in zip(all_digits, weights))

    # 驗證檢查碼
    # 如果加權總和可以被 10 整除，則有效
    return weighted_sum % 10 == 0

def is_valid_luhn(card_number: Optional[str]) -> bool:
    if not card_number or not isinstance(card_number, str):
        return False
    
    # 1. 移除所有非數字字元
    digits_str = "".join(filter(str.isdigit, card_number))
    
    # 2. 檢查長度是否合理
    if not 13 <= len(digits_str) <= 19:
        return False

    # 3. Luhn 演算法 (使用函式二的正確邏輯)
    digits = [int(d) for d in digits_str]
    # 從倒數第二個數字開始，往左每隔一項乘以 2
    for i in range(len(digits) - 2, -1, -2):
        doubled_digit = digits[i] * 2
        # 如果大於 9，則將其位數相加
        digits[i] = doubled_digit // 10 + doubled_digit % 10

    # 4. 將所有數字加總並驗證
    total = sum(digits)
    return total % 10 == 0