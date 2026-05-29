from flask import Blueprint, request
import os
import tempfile
from src.api.utils import api_success, api_error

ocr_bp = Blueprint('ocr', __name__, url_prefix='/api/ocr')


@ocr_bp.route('', methods=['POST'])
def ocr_recognize():
    """OCR 图片文字识别"""
    # 检查是否有文件
    if 'image' not in request.files:
        return api_error("请上传图片", 400)

    file = request.files['image']
    if not file.filename:
        return api_error("请选择图片文件", 400)

    # 检查文件类型
    allowed_types = {'image/jpeg', 'image/png', 'image/webp', 'image/bmp'}
    if file.content_type not in allowed_types:
        return api_error("仅支持 JPG/PNG/WebP/BMP 格式", 400)

    # 检查文件大小 (10MB)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > 10 * 1024 * 1024:
        return api_error("图片大小不能超过 10MB", 400)

    try:
        # 保存到临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=_get_extension(file.content_type)) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        # 调用 OCR
        text = _ocr_recognize(tmp_path)

        # 清理临时文件
        os.unlink(tmp_path)

        if not text:
            return api_error("未能识别文字，请尝试更清晰的图片", 400)

        return api_success({
            'text': text,
            'length': len(text)
        })

    except Exception as e:
        # 清理临时文件
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return api_error(f"识别失败: {str(e)}", 500)


def _get_extension(content_type):
    """获取文件扩展名"""
    extensions = {
        'image/jpeg': '.jpg',
        'image/png': '.png',
        'image/webp': '.webp',
        'image/bmp': '.bmp'
    }
    return extensions.get(content_type, '.jpg')


def _ocr_recognize(image_path):
    """调用 OCR 识别文字"""
    # 尝试使用 Tesseract
    try:
        import pytesseract
        from PIL import Image

        img = Image.open(image_path)

        # 中文 + 英文识别
        text = pytesseract.image_to_string(img, lang='chi_sim+eng', config='--psm 6')
        return text.strip()
    except ImportError:
        pass
    except Exception as e:
        print(f"Tesseract error: {e}")

    # 尝试使用百度 OCR API (如果有配置)
    try:
        import requests
        from src.config import config

        # 检查是否有百度 OCR 配置
        baidu_api_key = os.getenv('BAIDU_OCR_API_KEY')
        baidu_secret_key = os.getenv('BAIDU_OCR_SECRET_KEY')

        if baidu_api_key and baidu_secret_key:
            # 获取 access token
            token_url = 'https://aip.baidubce.com/oauth/2.0/token'
            token_res = requests.post(token_url, data={
                'grant_type': 'client_credentials',
                'client_id': baidu_api_key,
                'client_secret': baidu_secret_key
            })
            access_token = token_res.json().get('access_token')

            if access_token:
                # 调用 OCR
                ocr_url = f'https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token={access_token}'

                with open(image_path, 'rb') as f:
                    import base64
                    image_base64 = base64.b64encode(f.read()).decode()

                ocr_res = requests.post(ocr_url, data={
                    'image': image_base64,
                    'language_type': 'CHN_ENG'
                })

                result = ocr_res.json()
                if 'words_result' in result:
                    text = '\n'.join([item['words'] for item in result['words_result']])
                    return text.strip()
    except Exception as e:
        print(f"Baidu OCR error: {e}")

    # 如果都没有，返回提示
    raise Exception("OCR 服务未配置，请安装 Tesseract 或配置百度 OCR API")
