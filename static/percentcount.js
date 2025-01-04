    document.addEventListener("DOMContentLoaded", function () {
        // Проходим по всем таблицам
        document.querySelectorAll(".stat-block table").forEach(table => {
            // Получаем строки таблицы, кроме первой (заголовок)
            const rows = table.querySelectorAll("tbody tr");

            rows.forEach(row => {
                // Получаем ячейку с количеством матчей
                const matchesCell = row.cells[1]; // "Матчи" — это вторая колонка (индекс 1)
                const totalMatches = parseInt(matchesCell.textContent.trim(), 10);

                if (!isNaN(totalMatches) && totalMatches > 0) {
                    // Проходим по всем ячейкам после "Матчи"
                    for (let i = 2; i < row.cells.length; i++) {
                        const cell = row.cells[i];
                        const header = table.querySelector(`thead tr th:nth-child(${i + 1})`);

                        // Пропускаем ROI
                        if (header && header.textContent.includes("ROI")) {
                            continue;
                        }

                        const value = parseInt(cell.textContent.trim(), 10);
                        if (!isNaN(value)) {
                            // Вычисляем процент
                            const percentage = ((value / totalMatches) * 100).toFixed(2);
                            // Обновляем содержимое ячейки с процентом
                            cell.textContent = `${value} (${percentage}%)`;
                        }
                    }
                }
            });
        });
    });