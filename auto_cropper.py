import os
import tkinter as tk
from tkinter import filedialog, messagebox
import glob
from PIL import Image
import logging

def select_folder():
    """フォルダ選択ダイアログを表示し、選択されたフォルダパスを返す"""
    root = tk.Tk()
    root.withdraw()  # メインウィンドウを表示しない
    folder_path = filedialog.askdirectory(title="処理するフォルダを選択してください")
    return folder_path

def find_png_files(folder_path):
    """指定されたフォルダ内のPNGファイルを検索して一覧を返す"""
    if not folder_path:
        return []
    
    # フォルダ内のPNGファイルを検索
    png_pattern = os.path.join(folder_path, "*.png")
    png_files = glob.glob(png_pattern)
    
    return png_files

def detect_margins(image_path):
    """画像の余白を検出して上下左右の余白ピクセル数を返す"""
    try:
        # 画像を開く
        with Image.open(image_path) as img:
            # RGBAモードの場合はRGBに変換
            if img.mode == 'RGBA':
                # 透明部分を白色で埋める
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])  # 3はアルファチャンネル
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 画像のサイズを取得
            width, height = img.size
            
            # 画像データをピクセル配列に変換
            pixels = img.load()
            
            # 背景色を取得（四隅の平均）
            bg_samples = [
                pixels[0, 0],
                pixels[width-1, 0],
                pixels[0, height-1],
                pixels[width-1, height-1]
            ]
            
            # 最も頻度の高い色を背景色とする
            bg_color = max(set(bg_samples), key=bg_samples.count)
            
            # 余白を検出
            # 上部の余白
            top_margin = 0
            for y in range(height):
                is_margin_row = True
                for x in range(width):
                    # 背景色と異なる色があれば、余白ではない
                    if pixels[x, y] != bg_color:
                        is_margin_row = False
                        break
                if not is_margin_row:
                    break
                top_margin += 1
            
            # 下部の余白
            bottom_margin = 0
            for y in range(height-1, -1, -1):
                is_margin_row = True
                for x in range(width):
                    if pixels[x, y] != bg_color:
                        is_margin_row = False
                        break
                if not is_margin_row:
                    break
                bottom_margin += 1
            
            # 左側の余白
            left_margin = 0
            for x in range(width):
                is_margin_col = True
                for y in range(top_margin, height - bottom_margin):
                    if pixels[x, y] != bg_color:
                        is_margin_col = False
                        break
                if not is_margin_col:
                    break
                left_margin += 1
            
            # 右側の余白
            right_margin = 0
            for x in range(width-1, -1, -1):
                is_margin_col = True
                for y in range(top_margin, height - bottom_margin):
                    if pixels[x, y] != bg_color:
                        is_margin_col = False
                        break
                if not is_margin_col:
                    break
                right_margin += 1
            
            return {
                'top': top_margin,
                'bottom': bottom_margin,
                'left': left_margin,
                'right': right_margin,
                'width': width,
                'height': height
            }
    except Exception as e:
        error_msg = f"エラー: {image_path} の処理中に問題が発生しました: {e}"
        log_message(error_msg)
        return None

def check_image_sizes(png_files):
    """すべての画像が同じサイズかチェックする"""
    if not png_files:
        return True, None
    
    first_image = None
    try:
        with Image.open(png_files[0]) as img:
            first_size = img.size
            
        for file_path in png_files[1:]:
            with Image.open(file_path) as img:
                if img.size != first_size:
                    return False, (file_path, img.size, first_size)
        return True, first_size
    except Exception as e:
        return False, str(e)

def find_minimum_margins(png_files):
    """すべての画像から最小の余白を計算する"""
    if not png_files:
        return None
    
    all_margins = []
    for file_path in png_files:
        margins = detect_margins(file_path)
        if margins:
            all_margins.append(margins)
    
    if not all_margins:
        return None
    
    # 最小の余白を計算
    min_margins = {
        'top': min(m['top'] for m in all_margins),
        'bottom': min(m['bottom'] for m in all_margins),
        'left': min(m['left'] for m in all_margins),
        'right': min(m['right'] for m in all_margins),
        'width': all_margins[0]['width'],
        'height': all_margins[0]['height']
    }
    
    return min_margins

def crop_image_with_margins(image_path, margins, center_keep=False):
    """画像を指定された余白で切り取る
    
    Args:
        image_path: 画像ファイルのパス
        margins: 余白情報の辞書
        center_keep: 中心を維持するかどうか（デフォルトはFalse）
    """
    try:
        with Image.open(image_path) as img:
            # 画像のモードを保持
            original_mode = img.mode
            width = margins['width']
            height = margins['height']
            
            if center_keep:
                # 左右の余白で小さい方を左右に設定
                min_horizontal = min(margins['left'], margins['right'])
                # 上下の余白で小さい方を上下に設定
                min_vertical = min(margins['top'], margins['bottom'])
                
                # 切り取り範囲を計算（中心を維持）
                left = min_horizontal
                right = width - min_horizontal
                top = min_vertical
                bottom = height - min_vertical
                
                log_message(f"中心維持モード: 左右余白={min_horizontal}, 上下余白={min_vertical}")
            else:
                # 通常の切り取り（最小余白）
                left = margins['left']
                top = margins['top']
                right = width - margins['right']
                bottom = height - margins['bottom']
            
            # 画像を切り取る
            cropped_img = img.crop((left, top, right, bottom))
            
            # 元の画像モードを維持
            if cropped_img.mode != original_mode:
                cropped_img = cropped_img.convert(original_mode)
                
            return cropped_img
    except Exception as e:
        error_msg = f"エラー: {image_path} の切り取り中に問題が発生しました: {e}"
        log_message(error_msg)
        return None

def ensure_convert_directory(folder_path):
    """convertディレクトリを作成する（存在しない場合）"""
    convert_dir = os.path.join(folder_path, "convert")
    if not os.path.exists(convert_dir):
        try:
            os.makedirs(convert_dir)
            log_message(f"convertディレクトリを作成しました: {convert_dir}")
        except Exception as e:
            error_msg = f"エラー: convertディレクトリの作成中に問題が発生しました: {e}"
            log_message(error_msg)
            return None
    return convert_dir

def save_cropped_image(cropped_img, original_path, convert_dir):
    """切り取った画像を保存する"""
    try:
        # 元のファイル名を取得
        file_name = os.path.basename(original_path)
        
        # 保存先のパスを生成
        save_path = os.path.join(convert_dir, file_name)
        
        # 画像を保存
        log_message(f"")
        cropped_img.save(save_path)
        log_message(f"切り取った画像を保存しました: {save_path}")
        return save_path
    except Exception as e:
        error_msg = f"エラー: 画像の保存中に問題が発生しました: {e}"
        log_message(error_msg)
        return None

def setup_logging():
    """ログ設定を初期化する"""
    # ログファイルの設定
    logging.basicConfig(
        filename='auto_cropper.log',
        filemode='w',  # 上書きモード
        level=logging.INFO,
        format='%(message)s',  # タイムスタンプなし
        encoding='utf-8'  # UTF-8エンコーディング
    )

def log_message(message):
    """コンソールとログファイルの両方にメッセージを出力する"""
    print(message)
    logging.info(message)

def main():
    # ログ設定を初期化
    setup_logging()
    
    # フォルダ選択ダイアログを表示
    folder_path = select_folder()
    
    if not folder_path:
        # フォルダが選択されていない場合は処理を終了
        log_message("フォルダが選択されていません。")
        return
        
    # PNGファイルを検索
    png_files = find_png_files(folder_path)
    
    if not png_files:
        messagebox.showinfo("情報", "PNG画像が見つかりませんでした。")
        return
    
    log_message(f"{len(png_files)}個のPNG画像が見つかりました。")
    
    # 処理を続行するか確認ダイアログを表示
    if messagebox.askyesno("確認", f"{len(png_files)}個の画像が見つかりました。\n中心を維持して切り取りますか？"):
        center_keep = True
    else:
        center_keep = False
    
    # すべての画像が同じサイズかチェック
    same_size, result = check_image_sizes(png_files)
    if not same_size:
        if isinstance(result, tuple):
            file_path, size, first_size = result
            error_msg = f"画像サイズが一致しません。\n{file_path}のサイズ: {size[0]}x{size[1]}\n最初の画像のサイズ: {first_size[0]}x{first_size[1]}"
        else:
            error_msg = f"画像チェック中にエラーが発生しました: {result}"
        messagebox.showerror("エラー", error_msg)
        return
    
    # 各画像の余白を検出
    for file_path in png_files:
        log_message(f"\n画像ファイル: {file_path}")
        
        # 余白を検出
        margins = detect_margins(file_path)
        if margins:
            log_message(f"画像サイズ: {margins['width']}x{margins['height']}")
            log_message(f"上余白: {margins['top']} 下余白: {margins['bottom']} 左余白: {margins['left']} 右余白: {margins['right']}")
            log_message(f"余白を削除後の画像サイズ: {margins['width'] - margins['left'] - margins['right']}x{margins['height'] - margins['top'] - margins['bottom']}")
    
    # 最小の余白を計算
    min_margins = find_minimum_margins(png_files)
    result_msg = f"全ての画像の最小余白:\n上余白: {min_margins['top']} 下余白: {min_margins['bottom']} 左余白: {min_margins['left']} 右余白: {min_margins['right']}"
    log_message("\n" + result_msg)

    # convertディレクトリを作成
    convert_dir = ensure_convert_directory(folder_path)
    if not convert_dir:
        messagebox.showerror("エラー", "convertディレクトリの作成に失敗しました。")
        return
    
    # 画像を切り取って保存
    success_count = 0
    error_count = 0
        
    for file_path in png_files:
        # 画像を切り取る（center_keepパラメータを渡す）
        cropped_img = crop_image_with_margins(file_path, min_margins, center_keep)
        if cropped_img:
            # 切り取った画像を保存
            if save_cropped_image(cropped_img, file_path, convert_dir):
                success_count += 1
            else:
                error_count += 1
        else:
            error_count += 1
    
    # 処理結果を表示
    messagebox.showinfo("情報", "処理が完了しました。")

if __name__ == "__main__":
    main()
