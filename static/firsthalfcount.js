    function calculateStats(tableId, over05Id, over15Id) {
        let table = document.getElementById(tableId);
        let rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
        let totalMatches = rows.length;
        let over05Count = 0;
        let over15Count = 0;

        for (let row of rows) {
            let halfTimeScore = row.cells[4].innerText.split(' - ');
            let homeGoals = parseInt(halfTimeScore[0], 10);
            let awayGoals = parseInt(halfTimeScore[1], 10);
            let totalGoals = homeGoals + awayGoals;

            if (totalGoals > 0.5) over05Count++;
            if (totalGoals > 1.5) over15Count++;
        }

        let over05Percentage = ((over05Count / totalMatches) * 100).toFixed(2);
        let over15Percentage = ((over15Count / totalMatches) * 100).toFixed(2);

        document.getElementById(over05Id).innerText = `${over05Count}/${totalMatches} (${over05Percentage})`;
        document.getElementById(over15Id).innerText = `${over15Count}/${totalMatches} (${over15Percentage})`;
    }

    calculateStats('matches-team1', 'team1-over-0-5', 'team1-over-1-5');
    calculateStats('matches-team2', 'team2-over-0-5', 'team2-over-1-5');