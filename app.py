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



# =========================================================
# 工具函式區
# =========================================================

def normalize_row(row):
    """
    將單一橫向層資料整理成只包含 0/1 的 list。

    可接受格式：
    - [1, 0, 1, "", None]
    - {"values": [1, 0, 1]}

    功能：
    - 去除空白、None、"-"、"NA" 等無效值
    - 將字串數字轉成 int
    - 最終只保留 0 與 1
    """
    if isinstance(row, dict):
        row = row.get("values", [])

    normalized = []
    for x in row:
        # 先排除空值或不參與計算的符號
        if x in ("", None, " ", "-", "NA"):
            continue

        # 若是字串，先去除前後空白
        if isinstance(x, str):
            x = x.strip()
            if x == "":
                continue

        # 嘗試轉為整數
        try:
            v = int(x)
        except (TypeError, ValueError):
            continue

        # 只保留 0 或 1
        if v in (0, 1):
            normalized.append(v)

    return normalized


def count_runs(seq):
    """
    計算單一橫向層的 runs 數。

    runs 定義：
    相同值連續出現視為同一段，值改變時 run 數 +1

    例如：
    [1, 1, 0, 0, 1, 0] -> runs = 4
    分段為：
    11 / 00 / 1 / 0
    """
    if not seq:
        return 0

    runs = 1
    for i in range(1, len(seq)):
        if seq[i] != seq[i - 1]:
            runs += 1
    return runs


def row_entropy(seq):
    """
    計算單一橫向層的 entropy。

    這裡以該橫向層內部的 0/1 分布計算 Shannon entropy。
    若該層全是 0 或全是 1，entropy = 0。
    """
    if not seq:
        return 0.0

    n = len(seq)
    n1 = sum(seq)
    n0 = n - n1

    entropy = 0.0

    if n1 > 0:
        p1 = n1 / n
        entropy += -(p1 * math.log2(p1))

    if n0 > 0:
        p0 = n0 / n
        entropy += -(p0 * math.log2(p0))

    return entropy


def calculate_total_entropy(rows, move_count):
    """
    計算橫向總熵值 (Total Entropy)
    """
    # 總可能連結數 (T)
    T = move_count * (move_count - 1) // 2
    if T <= 0:
        return 0.0, 0
    
    # 計算每一橫排的 link 數量
    links = [sum(normalize_row(row)) for row in rows]
    total_links = sum(links)
    
    # 計算有 link 的橫排 Entropy
    H = sum(-(L / T) * math.log2(L / T) for L in links if L > 0)
    
    # 補上空點 (Empty points) 的 Entropy
    E = T - total_links
    if E > 0:
        H += -(E / T) * math.log2(E / T)
        
    return H, total_links


def normal_approx_probability(n1, n2, run_count):
    """
    大樣本時，使用常態近似計算 run test probability。

    參數：
    - n1：該層 links 數量
    - n2：該層 nodes 數量
    - run_count：該層實際 runs 數

    回傳：
    - 該 runs 對應的雙尾機率
    """
    N = n1 + n2
    if N <= 1 or n1 == 0 or n2 == 0:
        return 1.0

    # run test 的期望值
    mu = (2 * n1 * n2) / N + 1

    # run test 的變異數
    variance = (2 * n1 * n2 * (2 * n1 * n2 - N)) / (N**2 * (N - 1))

    if variance <= 0:
        return 1.0

    sigma = math.sqrt(variance)

    # 計算 Z 分數
    z = (run_count - mu) / sigma

    # 轉為雙尾 p-value
    p_value = 2 * (1 - norm.cdf(abs(z)))
    return float(p_value)


# =========================================================
# 小樣本 Run Test 查表區
# key = (較小值, 較大值, runs)
# value = 對應的非累積 probability
# 你之後可以依自己的完整表格繼續補充
# =========================================================
RUN_TEST_LOOKUP = {
    (2, 3, 2): 0.2,
    (2, 3, 3): 0.3,
    (2, 3, 4): 0.4,
    (2, 3, 5): 0.1,

    (2, 4, 2): 0.133,
    (2, 4, 3): 0.267,
    (2, 4, 4): 0.4,
    (2, 4, 5): 0.2,

    (2, 5, 2): 0.095,
    (2, 5, 3): 0.238,
    (2, 5, 4): 0.381,
    (2, 5, 5): 0.286,
}


def lookup_run_probability(n1, n2, run_count):
    """
    小樣本時查表取得 probability。

    為避免順序差異，例如 (2,5) 與 (5,2) 被視為同一組，
    這裡會先排序後再查表。
    """
    a, b = sorted((n1, n2))
    return RUN_TEST_LOOKUP.get((a, b, run_count))


def run_test_probability(n1, n2, run_count):
    """
    計算單一橫向層的 probability。

    規則：
    1. 若某層全為 link 或全為 node，直接回傳 1.0
    2. 若為小樣本（n1 < 10 且 n2 < 10），優先查 lookup table
    3. 若查表沒有資料，退回常態近似
    4. 若為大樣本，直接用常態近似
    """
    if n1 == 0 or n2 == 0:
        return 1.0

    if n1 < 10 and n2 < 10:
        p = lookup_run_probability(n1, n2, run_count)
        if p is not None:
            return float(p)

    return normal_approx_probability(n1, n2, run_count)


def summarize_rows(rows, move_count):
    """
    核心統計函式：統整 Entropy、Runs 與 Probability
    """
    total_runs = 0
    total_probability_sum = 0.0
    row_details = []

    # 1. 橫向總熵值計算
    total_entropy, total_links = calculate_total_entropy(rows, move_count)

    # 2. 逐行計算 Runs 與 Probability
    for idx, raw_row in enumerate(rows, start=1):
        seq = normalize_row(raw_row)

        if not seq:
            row_details.append({
                "row_index": idx, "length": 0, "links": 0, "nodes": 0, 
                "runs": 0, "probability": 0.0
            })
            continue

        n1 = sum(seq)
        n2 = len(seq) - n1

        # 新版 Runs 計算：數值改變時 +1
        runs = 1 + sum(seq[i] != seq[i - 1] for i in range(1, len(seq))) if seq else 0

        # 計算該層的檢定機率
        prob = run_test_probability(n1, n2, runs)

        total_runs += runs
        total_probability_sum += prob

        row_details.append({
            "row_index": idx,
            "length": len(seq),
            "links": n1,
            "nodes": n2,
            "runs": runs,
            "probability": round(prob, 6),
        })

    return {
        "total_links": total_links,
        "total_entropy": total_entropy,
        "total_runs": total_runs,
        "total_probability_sum": total_probability_sum,
        "row_details": row_details
    }


# =========================================================
# API：一次計算完整 Linkography 指標
# =========================================================

@app.route("/api/calculate_linkography_metrics", methods=["POST"])
def calculate_linkography_metrics():
    """
    一次回傳完整指標：
    - total_links
    - entropy
    - runs
    - p

    前端傳入格式：
    {
      "move_count": 14,
      "rows": [
        [1,0,0,0,0,0,0,0,0,0,0,0,1],
        [1,0,0,0,0,0,0,0,0,0,0,0],
        ...
      ]
    }
    """
    data = request.json
    move_count = data.get("move_count")
    rows = data.get("rows", [])

    # 檢查 move 數是否有效
    if not isinstance(move_count, int) or move_count <= 1:
        return jsonify({"error": "move_count 無效"}), 400

    # 檢查 rows 是否有資料
    if not rows or not isinstance(rows, list):
        return jsonify({"error": "rows 無效"}), 400

    result = summarize_rows(rows)

    return jsonify({
        "move_count": move_count,
        "total_links": result["total_links"],
        "entropy": round(result["total_entropy"], 6),
        "runs": result["total_runs"],
        "p": round(result["total_probability_sum"], 6),
        "row_details": result["row_details"],
    })


# =========================================================
# API：只算 entropy
# =========================================================

@app.route("/api/calculate_entropy", methods=["POST"])
def calculate_entropy():
    data = request.json
    move_count = data.get("move_count")
    rows = data.get("rows", [])

    if not isinstance(move_count, int) or move_count <= 1:
        return jsonify({"error": "Move 數量未設定或無效。"}), 400

    if not rows or not isinstance(rows, list):
        return jsonify({"error": "未提供任何橫排資料 (rows)。請確認前端傳送的資料格式。"}), 400

    # 必須傳入 move_count 給 summarize_rows 計算 T 值
    result = summarize_rows(rows, move_count)

    return jsonify({
        "creativity": round(result["total_entropy"], 6),
        "total_links": result["total_links"],
        "row_details": result["row_details"]
    })


# =========================================================
# API：只算 runs 與 p
# =========================================================

@app.route("/api/calculate_run_test", methods=["POST"])
def calculate_run_test():
    data = request.json
    move_count = data.get("move_count")
    rows = data.get("rows", [])

    if not isinstance(move_count, int) or move_count <= 1:
        return jsonify({"error": "Move 數量未設定或無效。"}), 400

    if not rows or not isinstance(rows, list):
        return jsonify({"error": "未提供任何橫排資料 (rows)。請確認前端傳送的資料格式。"}), 400

    result = summarize_rows(rows, move_count)

    total_run_sum = result["total_runs"]
    total_probability_sum = result["total_probability_sum"]

    # 依照你的邏輯回歸公式更新
    try:
        exponent = -(-69.15 + 0.077 * move_count + 0.001 * total_run_sum + 6.95 * total_probability_sum)
        logistic_p = 1 / (1 + math.exp(exponent))
    except OverflowError:
        # 防止 exp 數值過大溢位
        logistic_p = 0.0 if exponent > 0 else 1.0

    return jsonify({
        "runs": total_run_sum,
        "p": round(total_probability_sum, 6),
        "logistic_p": round(logistic_p, 6),
        "row_details": result["row_details"]
    })


if __name__ == "__main__":
    # debug=True：開發時方便除錯，正式上線時可改為 False
    app.run(debug=True)
