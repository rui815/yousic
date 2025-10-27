# ユーザー登録/accounts/spotify_client.py (client_auth.pyを元に修正)
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む（settings.pyで処理済みの場合は不要な場合あり）
load_dotenv()

# スコープ（必要な権限）
scope = "user-read-currently-playing user-read-recently-played"

def get_spotify_client(user_id):
    """
    DjangoのユーザーID(int)を基にキャッシュパスを決定し、認証済みクライアントを返す。
    """
    # ユーザーIDはDjangoのuser.pk (e.g. 1, 2, 3...) の想定
    if not os.path.exists('.cache'):
        os.makedirs('.cache')

    # キャッシュファイル名は直接ユーザーIDを使用
    cache_file_path = f".cache/{user_id}.json"

    # 環境変数の取得
    client_id = os.getenv('SPOTIPY_CLIENT_ID')
    client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
    redirect_uri = os.getenv('SPOTIPY_REDIRECT_URI')

    # 認証マネージャーを返す
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope,
        cache_path=cache_file_path,
        show_dialog=True
    ))

# 認証開始/コールバックのロジック（DjangoのViewに分割するため、元のperform_initial_authはここでは省略）
# DjangoのView側でAuth ManagerからURLを取得し、リダイレクト処理を行います。