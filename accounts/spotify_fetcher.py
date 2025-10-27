# ユーザー登録/accounts/spotify_fetcher.py (track_fetcher.pyを元に修正)
from .spotify_client import get_spotify_client # 変更後のclient_auth.pyからインポート

def get_track_info_for_user(user_id):
    """
    指定されたユーザーの現在、または直近再生した曲の情報を取得する関数。
    """
    try:
        # DjangoユーザーIDを渡す
        sp = get_spotify_client(user_id)
        current_track = sp.current_user_playing_track()
        
        if current_track and current_track.get('is_playing'):
            return current_track
        else:
            # 現在再生中の曲がない、または一時停止中の場合、直近再生した曲を取得
            recently_played = sp.current_user_recently_played(limit=1)
            # recently_played は 'items' キーを持つ辞書（リスト）
            return recently_played if recently_played and recently_played.get('items') else None
            
    except Exception as e:
        # トークンの期限切れなど、API呼び出しエラーを処理
        # ここで例外処理を行うことで、View側で簡単にエラーハンドリングできる
        print(f"ユーザー {user_id} の曲情報を取得中にエラーが発生しました: {e}")
        return {"error": str(e), "message": "Spotify APIトークンが無効または期限切れです。再認証が必要です。"}