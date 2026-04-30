from cryptography.fernet import Fernet
import base64
import os
from dotenv import load_dotenv

load_dotenv()

def generate_key():
    """生成加密密钥"""
    return Fernet.generate_key()

def get_fernet():
    """获取Fernet加密实例"""
    encryption_key = os.getenv('ENCRYPTION_KEY', 'text_analysis_system_key_2026')
    # 将密钥转换为Fernet所需的格式
    key = base64.urlsafe_b64encode(encryption_key.ljust(32)[:32].encode())
    return Fernet(key)

def encrypt_string(data):
    """加密字符串"""
    fernet = get_fernet()
    return fernet.encrypt(data.encode()).decode()

def decrypt_string(data):
    """解密字符串"""
    fernet = get_fernet()
    try:
        return fernet.decrypt(data.encode()).decode()
    except:
        return data  # 如果解密失败，返回原始数据

def encrypt_file(file_path):
    """加密文件"""
    fernet = get_fernet()
    with open(file_path, 'rb') as f:
        data = f.read()
    encrypted_data = fernet.encrypt(data)
    with open(file_path + '.encrypted', 'wb') as f:
        f.write(encrypted_data)

def decrypt_file(encrypted_file_path, output_path):
    """解密文件"""
    fernet = get_fernet()
    with open(encrypted_file_path, 'rb') as f:
        encrypted_data = f.read()
    decrypted_data = fernet.decrypt(encrypted_data)
    with open(output_path, 'wb') as f:
        f.write(decrypted_data)