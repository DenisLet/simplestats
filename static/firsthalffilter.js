function filterByHalfTimeScore() {
    const filterValue = document.getElementById('ht-score-filter').value.trim();
    const tables = document.querySelectorAll('table[id^="matches-team"]');


    const scoreRegex = /^\d+\s*-\s*\d+$/;

    if (filterValue === '' || !scoreRegex.test(filterValue)) {

        tables.forEach(table => {
            const rows = table.querySelectorAll('tbody tr');
            rows.forEach(row => {
                row.style.display = '';
            });
        });
        return;
    }

    const normalizedFilterValue = filterValue.replace(/\s/g, '').replace('-', ' - ');

    tables.forEach(table => {
        const rows = table.querySelectorAll('tbody tr');

        rows.forEach(row => {
            const halfTimeScore = row.querySelector('td:nth-child(5)').innerText.trim();
            if (halfTimeScore === normalizedFilterValue) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    });
}
