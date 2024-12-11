import os
import sqlite3
from flask import Flask, redirect, render_template, request, session, jsonify
import math 
from scipy.stats import norm  # 確保引入 norm 用於正態分佈計算

# 配置應用程式
app = Flask(__name__)

# 配置 session 使用 cookies
app.secret_key = os.urandom(24)

# 配置 SQLite 資料庫
db_connection = sqlite3.connect("linkography.db", check_same_thread=False)
db = db_connection.cursor()

@app.after_request
def after_request(response):
    """確保回應不會被快取"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/", methods=["GET", "POST"])
def index():
    """處理首頁請求"""
    if request.method == "POST":
        move_count = request.form.get("move_count")
        
        if not move_count or not move_count.isdigit():
            return render_template("index.html", error="請選擇有效的 move 數量。Please select a valid move quantity.")
        
        # 將 move 數量儲存在 session 中
        session["move_count"] = int(move_count)
        return redirect("/dashboard")
    
    return render_template("index.html")

@app.route("/dashboard", methods=["GET"])
def dashboard():
    """顯示 Linkography 儀表板"""
    if "move_count" not in session:
        return redirect("/")
    
    # 將 move 數量傳遞給儀表板模板
    move_count = session["move_count"]
    return render_template("dashboard.html", move_count=move_count)

@app.route("/api/linkography_data", methods=["GET"])
def linkography_data():
    """API 提供 Linkography 的資料"""
    if "move_count" not in session:
        return jsonify({"error": "Move 數量未設定。The number of moves has not been set yet."}), 400
    
    move_count = session["move_count"]
    
    # 生成基本的 Linkography 資料（目前只包含 move）
    moves = [{"id": i + 1, "name": f"Move {i + 1}"} for i in range(move_count)]
    
    return jsonify({"moves": moves})

@app.route("/api/update_link", methods=["POST"])
def update_link():
    """更新 link 的狀態（選中/未選中）"""
    data = request.json
    link_id = data.get("link_id")
    state = data.get("state")  # True 或 False
    
    # 這裡可以更新資料庫中對應 link 的狀態
    # 範例：db.execute("UPDATE links SET selected = ? WHERE id = ?", (state, link_id))
    
    # 暫時返回模擬回應
    return jsonify({"message": "Link 狀態更新成功", "link_id": link_id, "state": state})

@app.route("/api/calculate_entropy", methods=["POST"])
def calculate_entropy():
    """計算總熵創意值"""
    data = request.json
    links = data.get("links", [])  # 節點資料
    move_count = data.get("move_count")  # 從前端獲取 move 數量

    if not links:
        return jsonify({"error": "未提供任何 links 資料。No links data provided"}), 400
    
    if not move_count or not isinstance(move_count, int):
        return jsonify({"error": "Move 數量未設定或無效。The number of moves has not been set yet."}), 400
    

    # 計算總點數並初始化每一橫排的熵計算資料
    total_points = (move_count - 1) * move_count // 2
    row_entropies = [0] * (move_count - 1)  # 每一橫排的初始打點數量

    # 統計每一橫排的打點數量
    for link in links:
        move1 = link.get("move1")
        move2 = link.get("move2")
        if move1 is not None and move2 is not None:
            row = move2 - move1 - 1
            row_entropies[row] += 1

    # 計算每一橫排的熵值
    total_entropy = 0
    for row_count in row_entropies:
        if row_count > 0:
            probability = row_count / total_points
            total_entropy += -probability * math.log2(probability)

    # 計算空點熵值
    empty_points = total_points - len(links)
    if empty_points > 0:
        empty_probability = empty_points / total_points
        total_entropy += -empty_probability * math.log2(empty_probability)

    # 返回總熵創意值
    return jsonify({"creativity": total_entropy})

@app.route("/api/calculate_run_test", methods=["POST"])
def calculate_run_test():
    """計算總機率和和總run數，用於 Logistic Regression"""
    data = request.json
    rows = data.get("rows", [])  # 包含每橫排的數據
    move_count = data.get("move_count")  # 從前端獲取 move 數量

    if not rows:
        return jsonify({"error": "未提供任何橫排資料。No horizontal data provided."}), 400
    
    # 計算總run數和
    total_run_sum = sum(row["run_count"] for row in rows)

    # 計算總機率和
    total_probability_sum = 0
    for row in rows:
        n1 = row["n1"]
        n2 = row["n2"]
        run_count = row["run_count"]

        # 使用計算公式而非查表
        _, p_value = run_test_probability(n1, n2, run_count)
        total_probability_sum += p_value

    # Logistic Regression 計算
    z = -69.15 + 0.077 * move_count + 0.001 * total_run_sum + 6.95 * total_probability_sum
    p = 1 / (1 + math.exp(-z))

    return jsonify({"p_value": p, "total_run_sum": total_run_sum, "total_probability_sum": total_probability_sum})

def run_test_probability(n1, n2, run_count):
    """計算 Run Test 機率分布值 param n1: 第一類型的數據點數量 param n2: 第二類型的數據點數量 param R: 序列中的實際連數 (run) return: Z 值和對應的機率值 (p-value)"""
    
    # 總數 N
    N = n1 + n2
    
    # 檢查避免數學錯誤
    if N <= 1 or n1 == 0 or n2 == 0:
        return None, 1.0  # 如果數據不足，返回最大可能性
    
    # 計算期望值 (mu_R) 和標準差 (sigma_R)
    mu_R = (2 * n1 * n2) / N + 1
    sigma_R = math.sqrt((2 * n1 * n2 * (2 * n1 * n2 - N)) / (N**2 * (N - 1)))
    
    # 計算 Z 值
    Z = (run_count - mu_R) / sigma_R
    
    # 計算機率 (p-value) 使用標準正態分佈
    p_value = 2 * (1 - norm.cdf(abs(Z)))  # 雙尾檢定
    
    return Z, p_value

if __name__ == "__main__":
    app.run(debug=True)
