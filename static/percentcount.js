document.addEventListener("DOMContentLoaded", function () {

    document.querySelectorAll(".stat-block table").forEach(table => {

        const rows = table.querySelectorAll("tbody tr");

        rows.forEach(row => {

            const matchesCell = row.cells[1]; //
            const totalMatches = parseInt(matchesCell.textContent.trim(), 10);

            if (!isNaN(totalMatches) && totalMatches > 0) {

                for (let i = 2; i < row.cells.length; i++) {
                    const cell = row.cells[i];
                    const header = table.querySelector(`thead tr th:nth-child(${i + 1})`);


                    if (cell.classList.contains('max-ft') || cell.classList.contains('min-ft')) {
                        continue;
                    }


                    if (header && header.textContent.includes("ROI")) {
                        continue;
                    }

                    const value = parseInt(cell.textContent.trim(), 10);
                    if (!isNaN(value)) {

                        const percentage = ((value / totalMatches) * 100).toFixed(2);

                        cell.textContent = `${value} (${percentage}%)`;


                        if (percentage < 10) {
                            cell.style.backgroundColor = "#D32F2F";
                            cell.style.color = "white"; //
                        } else if (percentage < 30) {
                            cell.style.backgroundColor = "#F44336";
                            cell.style.color = "white";
                        } else if (percentage > 90) {
                            cell.style.backgroundColor = "#388E3C";
                            cell.style.color = "white";
                        } else if (percentage > 70) {
                            cell.style.backgroundColor = "#4CAF50";
                            cell.style.color = "white";
                        } else {

                            cell.style.backgroundColor = "";
                            cell.style.color = "";
                        }
                    }
                }
            }
        });
    });
});
