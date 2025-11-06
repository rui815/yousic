// MARK: - Codable Models

/// ユーザー登録時にAPIへ送信するデータ
struct RegistrationRequest: Codable {
    // ユーザー名
    let username: String
    // パスワード
    let password: String
    // 💡 追加: メールアドレス
    let email: String
}

import Foundation

/// 認証関連のAPI通信を管理するサービス
class AuthService {
    
    private let registrationURL = URL(string: "https://yousic.onrender.com/api/accounts/register/")! // ⚠️ URLを置き換えてください

    /**
     ユーザー登録APIを呼び出す関数
     - Parameters:
       - request: ユーザー名、パスワード、メールアドレスを含むリクエストデータ
       - completion: 処理結果を非同期で受け取るためのクロージャ (成功時は Void、失敗時は Error)
     */
    func registerUser(request: RegistrationRequest, completion: @escaping (Result<Void, Error>) -> Void) {
        
        var urlRequest = URLRequest(url: registrationURL)
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // エンコード処理 (RegistrationRequestの内容は更新されているが、処理自体は同じ)
        do {
            let jsonData = try JSONEncoder().encode(request)
            urlRequest.httpBody = jsonData
        } catch {
            completion(.failure(error))
            return
        }

        // リクエスト実行 (処理ロジックは変更なし)
        let task = URLSession.shared.dataTask(with: urlRequest) { data, response, error in
            
            if let error = error {
                completion(.failure(error))
                return
            }
            
            guard let httpResponse = response as? HTTPURLResponse, (200...201).contains(httpResponse.statusCode) else {
                let statusCode = (response as? HTTPURLResponse)?.statusCode ?? 0
                let error = NSError(domain: "", code: statusCode, userInfo: [NSLocalizedDescriptionKey: "登録に失敗しました (ステータスコード: \(statusCode))"])
                completion(.failure(error))
                return
            }
            
            // 成功と判断
            completion(.success(()))
        }
        
        task.resume()
    }
}

import SwiftUI

struct RegisterView: View {
    // ユーザー入力を保持するState
    @State private var username = ""
    @State private var password = ""
    // 💡 追加: email
    @State private var email = ""
    @State private var registrationMessage = ""
    
    private let authService = AuthService()

    var body: some View {
        VStack(spacing: 20) {
            Text("新規ユーザー登録")
                .font(.largeTitle).bold()

            TextField("ユーザー名を入力", text: $username)
                .padding().background(Color(.systemGray6)).cornerRadius(8)
            
            // 💡 追加: メールアドレス入力フィールド
            TextField("メールアドレスを入力", text: $email)
                .padding()
                .background(Color(.systemGray6))
                .cornerRadius(8)
                .keyboardType(.emailAddress) // メールアドレスに適したキーボードを設定
                .autocapitalization(.none)    // 自動大文字化をオフ

            SecureField("パスワードを入力", text: $password)
                .padding().background(Color(.systemGray6)).cornerRadius(8)

            Button("登録する") {
                performRegistration()
            }
            .frame(maxWidth: .infinity).padding()
            .background(Color.green).foregroundColor(.white).cornerRadius(10)
            
            Text(registrationMessage)
                .foregroundColor(registrationMessage.contains("成功") ? .green : .red)
                .padding(.top, 10)
        }
        .padding()
    }

    // 登録処理を実行するメソッド
    func performRegistration() {
        // 💡 修正: requestの初期化にemailを追加
        let request = RegistrationRequest(
            username: username,
            password: password,
            email: email
        )
        
        authService.registerUser(request: request) { result in
            DispatchQueue.main.async {
                switch result {
                case .success:
                    self.registrationMessage = "🎉 登録が成功しました！"
                    
                case .failure(let error):
                    self.registrationMessage = "🚨 登録失敗: \(error.localizedDescription)"
                }
            }
        }
    }
}
