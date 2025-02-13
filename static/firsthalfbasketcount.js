function calculateMinMaxScoresForHalf(tableId) {
    let rows = document.querySelectorAll(`#${tableId} tbody tr`);
    let homeScores = [];
    let awayScores = [];
    let totalScores = [];

    rows.forEach(row => {
        let firstQuarter = row.querySelector('td:nth-child(5)');
        let secondQuarter = row.querySelector('td:nth-child(6)');

        if (firstQuarter && secondQuarter) {
            let [home1, away1] = firstQuarter.textContent.split(' - ').map(Number);
            let [home2, away2] = secondQuarter.textContent.split(' - ').map(Number);

            let homeTotal = home1 + home2;
            let awayTotal = away1 + away2;

            homeScores.push(homeTotal);
            awayScores.push(awayTotal);
            totalScores.push(homeTotal + awayTotal);
        }
    });

    return {
        home: { min: Math.min(...homeScores), max: Math.max(...homeScores) },
        away: { min: Math.min(...awayScores), max: Math.max(...awayScores) },
        total: { min: Math.min(...totalScores), max: Math.max(...totalScores) }
    };
}

function updateMinMaxDisplayHalf(teamId, stats) {
    document.getElementById(`bb_half_${teamId}-min`).textContent = stats.min;
    document.getElementById(`bb_half_${teamId}-max`).textContent = stats.max;
}

function updateTotalMinMaxDisplayHalf(teamId, totalStats) {
    document.getElementById(`total-min-bb_half_${teamId}`).textContent = totalStats.min;
    document.getElementById(`total-max-bb_half_${teamId}`).textContent = totalStats.max;
}


let halfTeam1Stats = calculateMinMaxScoresForHalf('matches-team1');
let halfTeam2Stats = calculateMinMaxScoresForHalf('matches-team2');


updateMinMaxDisplayHalf('team1', halfTeam1Stats.home);
updateMinMaxDisplayHalf('team2', halfTeam2Stats.away);
updateTotalMinMaxDisplayHalf('team1', halfTeam1Stats.total);
updateTotalMinMaxDisplayHalf('team2', halfTeam2Stats.total);
