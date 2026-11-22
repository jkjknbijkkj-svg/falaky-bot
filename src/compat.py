"""
إصلاحات توافق لازمة قبل استعمال moviepy.

moviepy 1.0.3 ما زال ينادي Image.ANTIALIAS، وقد أزالته Pillow 10.
أي استدعاء لـ clip.resize() ينهار بدون هذا الإصلاح — وهو ما يحدث في
التركيب النهائي وفي البطاقة البديلة.

يُستورد في أعلى كل وحدة تستعمل moviepy.
"""

from PIL import Image

if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS
if not hasattr(Image, "LANCZOS"):
    Image.LANCZOS = Image.Resampling.LANCZOS
if not hasattr(Image, "BILINEAR"):
    Image.BILINEAR = Image.Resampling.BILINEAR
if not hasattr(Image, "BICUBIC"):
    Image.BICUBIC = Image.Resampling.BICUBIC
if not hasattr(Image, "NEAREST"):
    Image.NEAREST = Image.Resampling.NEAREST
