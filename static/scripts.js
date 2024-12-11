document.addEventListener("DOMContentLoaded", function () {
    const canvas = document.getElementById("linkography-canvas");
    const context = canvas.getContext("2d");
    const generateButton = document.getElementById("generate-button");
    const entropyButton = document.getElementById("calculate-entropy-button");
    const runTestButton = document.getElementById("calculate-run-test-button");
    const moveCountInput = document.getElementById("move-count");

    const canvasPadding = 40; // Canvas邊距
    canvas.width = 3600; // 畫布寬度
    canvas.height = 1900; // 畫布高度

    const moveSpacing = (canvas.width - 2 * canvasPadding) / 118; // 間距縮小一半
    const diagonalSpacing = 30; // 斜線節點之間的垂直距離
    let moveCount = 10; // 預設move數量
    const linkNodes = []; // 儲存節點資料

    function drawLinkography() {
        // 清空畫布
        context.clearRect(0, 0, canvas.width, canvas.height);

        const movePoints = [];

        // 繪製黑點和數字
        for (let i = 0; i < moveCount; i++) {
            const x = canvasPadding + i * moveSpacing;
            const y = canvasPadding;

            // 黑點
            context.beginPath();
            context.arc(x, y, 5, 0, 2 * Math.PI);
            context.fillStyle = "black";
            context.fill();
            context.stroke();

            // 數字
            context.font = "12px Arial";
            context.fillStyle = "black";
            context.fillText(`${i + 1}`, x - 4, y - 10);

            movePoints.push({ x, y }); // 儲存move點
        }

        // 繪製灰色斜線和空節點
        linkNodes.forEach((node) => {
            context.beginPath();
            context.arc(node.x, node.y, 5, 0, 2 * Math.PI);
            context.fillStyle = node.selected ? "#00008B" : "white"; // 深藍色或白色
            context.fill();
            context.strokeStyle = "gray"; // 空節點外框
            context.stroke();
        });
    }

    // 初始化節點
    function initializeLinkNodes() {
        const movePoints = [];
        for (let i = 0; i < moveCount; i++) {
            const x = canvasPadding + i * moveSpacing;
            const y = canvasPadding;
            movePoints.push({ x, y });
        }

        linkNodes.length = 0; // 清空節點
        for (let i = 0; i < movePoints.length; i++) {
            for (let j = i + 1; j < movePoints.length; j++) {
                const startX = movePoints[i].x;
                const startY = movePoints[i].y;
                const endX = movePoints[j].x;
                const endY = startY + (j - i) * diagonalSpacing;

                if (endY >= canvas.height - canvasPadding) break;

                const nodeX = (startX + endX) / 2;
                const nodeY = (startY + endY) / 2;

                linkNodes.push({
                    x: nodeX,
                    y: nodeY,
                    move1: i,
                    move2: j,
                    selected: false,
                });
            }
        }
    }

    // 處理滑鼠移動 (hover)
    canvas.addEventListener("mousemove", function (event) {
        const rect = canvas.getBoundingClientRect();
        const mouseX = event.clientX - rect.left;
        const mouseY = event.clientY - rect.top;

        let isHovering = false;
        linkNodes.forEach((node) => {
            const dx = mouseX - node.x;
            const dy = mouseY - node.y;
            const distance = Math.sqrt(dx * dx + dy * dy);

            if (distance <= 5) {
                isHovering = true;
                hoverNode = node;

                // 繪製淺藍色橫線
                const startX = canvasPadding + node.move1 * moveSpacing;
                const endX = canvasPadding + node.move2 * moveSpacing;
                const y = canvasPadding;

                context.clearRect(0, 0, canvas.width, canvas.height);
                drawLinkography();

                // 繪製與節點相交的紅色橫線
                context.beginPath();
                context.moveTo(startX, y);
                context.lineTo(endX, y);
                context.strokeStyle = "red";
                context.lineWidth = 2;
                context.stroke();

                // 在節點附近顯示小方框
                const boxWidth = 40;
                const boxHeight = 20;
                context.fillStyle = "lightyellow";
                context.fillRect(node.x - boxWidth / 2, node.y - 30, boxWidth, boxHeight);
                context.strokeStyle = "black";
                context.strokeRect(node.x - boxWidth / 2, node.y - 30, boxWidth, boxHeight);

                // 在方框內顯示文字
                context.font = "12px Arial";
                context.fillStyle = "black";
                context.fillText(
                    `${node.move1 + 1}, ${node.move2 + 1}`,
                    node.x - boxWidth / 2 + 5,
                    node.y - 15
                );
            }
        });

        if (!isHovering) {
            hoverNode = null;
            context.clearRect(0, 0, canvas.width, canvas.height);
            drawLinkography();
        }
    });

    // 處理滑鼠點擊
    canvas.addEventListener("click", function (event) {
        const rect = canvas.getBoundingClientRect();
        const mouseX = event.clientX - rect.left;
        const mouseY = event.clientY - rect.top;

        linkNodes.forEach((node) => {
            const dx = mouseX - node.x;
            const dy = mouseY - node.y;
            const distance = Math.sqrt(dx * dx + dy * dy);

            if (distance <= 5) {
                node.selected = !node.selected; // 切換節點選中狀態
                context.clearRect(0, 0, canvas.width, canvas.height);
                drawLinkography(); // 重新繪製節點

                // 更新到後端
                fetch("/api/update_link", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        link_id: `${node.move1}-${node.move2}`,
                        state: node.selected,
                    }),
                })
                    .then((response) => response.json())
                    .then((data) => {
                        console.log("Link updated:", data);
                    })
                    .catch((error) => {
                        console.error("Error updating link:", error);
                    });
            }
        });
    });

    // 生成按鈕點擊事件
    generateButton.addEventListener("click", function () {
        moveCount = parseInt(moveCountInput.value, 10);
        initializeLinkNodes();
        drawLinkography();
    }); 

    // 初次載入
    initializeLinkNodes();
    drawLinkography();

    // 熵計算按鈕事件
    entropyButton.addEventListener("click", function () {
        // 發送打點的資料到後端進行熵計算
        const selectedLinks = linkNodes
            .filter((node) => node.selected)
            .map((node) => ({ move1: node.move1, move2: node.move2 }));

        // 獲取當前的 move 數量
        const moveCount = parseInt(moveCountInput.value, 10);

        // 發送到後端
        fetch("/api/calculate_entropy", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ links: selectedLinks, move_count: moveCount  }),
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.error) {
                    alert(`Error: ${data.error}`);
                } else {
                    // 顯示計算結果
                    const resultElement = document.getElementById("entropy-result");
                    resultElement.textContent = `creative value：${data.creativity.toFixed(3)}`;
                }
            })
            .catch((error) => {
                console.error("Error calculating entropy:", error);
                alert("計算過程中發生錯誤，請稍後再試。An error occurred during calculation, please try again later.");
            });
    }); 

    // Run Test 和 Logistic Regression 按鈕事件
    runTestButton.addEventListener("click", function () {
        const moveCount = parseInt(moveCountInput.value, 10);
        const rows = linkNodes.reduce((acc, node) => {
            const rowIndex = node.move2 - node.move1 - 1;
            if (!acc[rowIndex]) acc[rowIndex] = { n1: 0, n2: 0, run_count: 0 };
            if (node.selected) acc[rowIndex].n1++;
            else acc[rowIndex].n2++;
            return acc;
        }, []);

        rows.forEach((row) => {
            row.run_count = row.n1 > 0 && row.n2 > 0 ? 2 : 1; // 簡化的run計算示例
        });

        fetch("/api/calculate_run_test", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ rows, move_count: moveCount }),
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.error) {
                    alert(`Error: ${data.error}`);
                } else {
                    const resultElement = document.getElementById("run-test-result");
                    resultElement.textContent = `probability value (p)：${data.p_value.toFixed(3)} | Total number of runs：${data.total_run_sum} | total probability sum：${data.total_probability_sum.toFixed(3)}`;
                }
            })
            .catch((error) => {
                console.error("Error calculating run test:", error);
                alert("計算過程中發生錯誤，請稍後再試。An error occurred during calculation, please try again later.");
            });
    });

});
