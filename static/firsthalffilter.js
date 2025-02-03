function filterByHalfTimeScore() {
    const filterValue = document.getElementById('ht-score-filter').value.trim();
    const tables = document.querySelectorAll('table[id^="matches-team"]');

    // Проверяем, что введенное значение соответствует формату "число - число"
    const scoreRegex = /^\d+\s*-\s*\d+$/;

    if (filterValue === '' || !scoreRegex.test(filterValue)) {
        // Если поле пустое или значение некорректное, показываем все строки
        tables.forEach(table => {
            const rows = table.querySelectorAll('tbody tr');
            rows.forEach(row => {
                row.style.display = ''; // Показать все строки
            });
        });
        return; // Завершаем функцию, если фильтр не должен применяться
    }

    const normalizedFilterValue = filterValue.replace(/\s/g, '').replace('-', ' - '); // Нормализуем формат ввода

    tables.forEach(table => {
        const rows = table.querySelectorAll('tbody tr');

        rows.forEach(row => {
            const halfTimeScore = row.querySelector('td:nth-child(5)').innerText.trim();
            if (halfTimeScore === normalizedFilterValue) {
                row.style.display = ''; // Показать строку
            } else {
                row.style.display = 'none'; // Скрыть строку
            }
        });
    });
}
