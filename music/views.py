from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import SongShare
from .serializers import SongShareSerializer
from accounts.models import CustomUser # フォロー関係の取得に利用

# Spotify APIライブラリ
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from django.utils import timezone
from datetime import timedelta # トークンの有効期限計算用
import os # .env ファイル読み込み用

# ----------------------------------------------------
# ★ Spotify API 関連のロジック（ヘルパー関数）
# ----------------------------------------------------

def get_spotify_api_client(user):
    """
    ユーザーのトークンを使ってSpotipyクライアントを取得します。
    トークンが切れていたら自動でリフレッシュします。
    """
    
    token_expired = False
    
    # --- ★ バグ修正箇所 (ここから) ---
    # 1. 有効期限がDBに保存されているかチェック
    if not user.spotify_token_expires_at:
        # 有効期限が None の場合は、リフレッシュが必須と判断
        print(f"有効期限 (expires_at) が設定されていません。トークンリフレッシュを実行します。")
        token_expired = True
    # 2. 有効期限が切れているかチェック
    elif user.spotify_token_expires_at < timezone.now():
        print(f"トークンが期限切れです (期限: {user.spotify_token_expires_at})。リフレッシュします。")
        token_expired = True
    # --- ★ バグ修正箇所 (ここまで) ---

    # トークンが期限切れの場合のみリフレッシュ処理を実行
    if token_expired:
        try:
            # .env ファイルから Spotify 認証情報を読み込む
            # (settings.py から読み込む方が望ましいが、views.pyでも可)
            client_id = os.environ.get('SPOTIPY_CLIENT_ID')
            client_secret = os.environ.get('SPOTIPY_CLIENT_SECRET')
            redirect_uri = os.environ.get('SPOTIPY_REDIRECT_URI') # settings.pyに設定したものが望ましい

            if not all([client_id, client_secret, redirect_uri, user.spotify_refresh_token]):
                print("エラー: Spotifyリフレッシュに必要な情報 (ID, Secret, URI, Refresh Token) が不足しています。")
                return None

            # SpotipyのOAuthマネージャーを初期化
            sp_oauth = SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope="user-read-currently-playing user-read-recently-played" # 必要なスコープ
            )

            # リフレッシュトークンを使って新しいアクセストークンを取得
            new_token_info = sp_oauth.refresh_access_token(user.spotify_refresh_token)
            
            print("Spotifyトークンのリフレッシュに成功しました。")

            # 新しいトークン情報をデータベース（userモデル）に保存
            user.spotify_access_token = new_token_info['access_token']
            user.spotify_refresh_token = new_token_info.get('refresh_token', user.spotify_refresh_token) # 新しいリフレッシュトークンが発行された場合のみ更新
            user.spotify_token_expires_at = timezone.now() + timedelta(seconds=new_token_info['expires_in'])
            user.save()
            
            print(f"新しい有効期限: {user.spotify_token_expires_at}")

        except spotipy.exceptions.SpotifyException as e:
            print(f"Spotifyトークンのリフレッシュに失敗しました: {e}")
            # リフレッシュに失敗した場合（例: ユーザーが連携を解除した）
            return None
        except Exception as e:
            print(f"予期せぬエラー（リフレッシュ処理中）: {e}")
            return None

    # 有効な（またはリフレッシュされた）アクセストークンでクライアントを初期化
    if user.spotify_access_token:
        return spotipy.Spotify(auth=user.spotify_access_token)
    
    print("有効なアクセストークンがありません。")
    return None

# ----------------------------------------------------
# API ビュー
# ----------------------------------------------------

class ShareCurrentSongView(APIView):
    """
    POST: 現在再生中の曲を取得し、SongShareとしてデータベースに保存します。
    (BeRealの通知に応じてSwiftアプリから叩かれるAPI)
    """
    permission_classes = [permissions.IsAuthenticated] # 認証必須

    def post(self, request, *args, **kwargs):
        user = request.user

        # 1. Spotify APIクライアントを取得 (トークンリフレッシュ含む)
        sp = get_spotify_api_client(user)

        if not sp:
            return Response(
                {"detail": "Spotify authentication required or token refresh failed."}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            track_info = None
            
            # 2. まず「今聞いている曲」を取得
            print(f"ユーザー({user.username})の再生中の曲を確認します...")
            current_track = sp.current_user_playing_track()

            if current_track and current_track.get('item'):
                print("再生中の曲が見つかりました。")
                track_info = current_track['item']
            else:
                # --- ★ 新機能 (ここから) ---
                # 再生中の曲がなかった場合、「直近再生した曲」を取得
                print("再生中の曲が見つかりません。直近の再生履歴を確認します。")
                recent_tracks = sp.current_user_recently_played(limit=1)
                
                if recent_tracks and recent_tracks.get('items'):
                    print("直近の再生履歴が見つかりました。")
                    # recent_tracks['items'] はリストなので、最初の要素の 'track' を使う
                    track_info = recent_tracks['items'][0]['track'] 
                else:
                    # どちらも見つからなかった場合
                    print("再生中の曲も直近の履歴もありません。")
                    return Response({"detail": "No track is currently playing or recently played."}, status=status.HTTP_404_NOT_FOUND)
                # --- ★ 新機能 (ここまで) ---

            # 3. 取得した曲をデータベースに保存
            song_share = SongShare.objects.create(
                user=user,
                spotify_track_id=track_info['id'],
                track_name=track_info['name'],
                artist_name=', '.join([artist['name'] for artist in track_info['artists']]), # 複数のアーティストを考慮
                album_cover_url=track_info['album']['images'][0]['url'] if track_info['album']['images'] else None # 簡略化
            )
            
            print(f"曲を保存しました: {track_info['name']}")
            serializer = SongShareSerializer(song_share)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except spotipy.exceptions.SpotifyException as e:
            # (例: APIレート制限、認証エラーなど)
            print(f"Spotify API Error: {e}")
            return Response({"detail": f"Spotify API Error: {e}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"予期せぬエラー（曲取得処理中）: {e}")
            return Response({"detail": f"An unexpected error occurred: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FollowingFeedView(generics.ListAPIView):
    """
    GET: 自分がフォローしているユーザーのSongShare一覧（フィード）を取得します。
    """
    serializer_class = SongShareSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        # 1. 自分がフォローしているユーザーのIDリストを取得
        # (CustomUserのrelated_name='follower_set'を利用)
        following_users_qs = CustomUser.objects.filter(follower_set__follower=user)
        
        # 2. そのユーザーたちのSongShareを日付順（新しい順）に取得
        # (SongShareのMeta.orderingで既に'-shared_at'が指定されている)
        queryset = SongShare.objects.filter(user__in=following_users_qs)
        
        return queryset
