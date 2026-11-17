(() => {
    const root = document.getElementById('seat-booking');
    if (!root) return;
    const occupied = new Set(JSON.parse(JSON.parse(document.getElementById('occupied-data').textContent)));
    const pending = new Set(JSON.parse(JSON.parse(document.getElementById('pending-data').textContent)));
    const selected = new Set();
    const seats = [...root.querySelectorAll('.hall-seat')];
    const list = document.getElementById('selected-seats-list');
    const input = document.getElementById('selected-seats-input');
    const submit = document.getElementById('booking-submit');
    const clear = document.getElementById('clear-selection');
    const cents = Number(root.dataset.price);
    const money = value => new Intl.NumberFormat('ru-RU', {style:'currency',currency:'RUB',maximumFractionDigits:2}).format(value / 100);
    const key = seat => `${seat.dataset.row}_${seat.dataset.seat}`;
    function render() {
        seats.forEach(seat => {
            const k = key(seat);
            const state = occupied.has(k) ? 'occupied' : pending.has(k) ? 'pending' : selected.has(k) ? 'selected' : 'free';
            seat.className = `hall-seat ${state}`;
            seat.disabled = state === 'occupied' || state === 'pending';
            seat.setAttribute('aria-pressed', String(state === 'selected'));
            seat.title = `Ряд ${seat.dataset.row}, место ${seat.dataset.seat} — ${ {'occupied':'занято','pending':'ожидает подтверждения','selected':'выбрано','free':'свободно'}[state] }`;
            seat.textContent = state === 'occupied' ? '×' : state === 'pending' ? '–' : seat.dataset.seat;
        });
        list.replaceChildren();
        [...selected].sort((a,b) => {const [r,s]=a.split('_').map(Number);const [rr,ss]=b.split('_').map(Number);return r-rr||s-ss;}).forEach(k => {
            const [row,seat] = k.split('_');
            const chip = document.createElement('button');
            chip.type = 'button'; chip.className = 'seat-chip';
            chip.textContent = `Ряд ${row} · Место ${seat} ×`;
            chip.setAttribute('aria-label', `Убрать ряд ${row}, место ${seat}`);
            chip.addEventListener('click', () => {selected.delete(k);render();});
            list.appendChild(chip);
        });
        if (!selected.size) {const p=document.createElement('p');p.textContent='Выберите места на схеме';list.appendChild(p);}
        input.value = [...selected].join(',');
        submit.disabled = clear.disabled = !selected.size;
        submit.textContent = selected.size ? `Забронировать · ${money(cents * selected.size)}` : 'Выберите места';
        document.getElementById('booking-total').textContent = money(cents * selected.size);
        document.getElementById('price-breakdown').textContent = `${selected.size} × ${money(cents)}`;
    }
    seats.forEach(seat => seat.addEventListener('click', () => {const k=key(seat);if(occupied.has(k)||pending.has(k))return;selected.has(k)?selected.delete(k):selected.add(k);render();}));
    clear.addEventListener('click', () => {selected.clear();render();});
    document.getElementById('booking-form').addEventListener('submit', event => {if(!selected.size)event.preventDefault();});
    render();
})();
