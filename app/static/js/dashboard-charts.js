document.addEventListener("DOMContentLoaded", function() {
    const statusDataScript = document.getElementById('status-data');
    const methodsDataScript = document.getElementById('methods-data');

    const statusDataRaw = statusDataScript ? JSON.parse(statusDataScript.textContent || '{}') : {};
    const methodsDataRaw = methodsDataScript ? JSON.parse(methodsDataScript.textContent || '{}') : {};

    const statusCanvas = document.getElementById('statusChart');
    if (statusCanvas) {
        const ctxStatus = statusCanvas.getContext('2d');
        new Chart(ctxStatus, {
            type: 'doughnut',
            data: {
                labels: Object.keys(statusDataRaw),
                datasets: [{
                    data: Object.values(statusDataRaw),
                    backgroundColor: [
                        '#10B981', // Pagado
                        '#F59E0B', // Parcial
                        '#EF4444'  // Pendiente
                    ],
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    }

    const methodsCanvas = document.getElementById('methodsChart');
    if (methodsCanvas) {
        const ctxMethods = methodsCanvas.getContext('2d');
        new Chart(ctxMethods, {
            type: 'bar',
            data: {
                labels: Object.keys(methodsDataRaw),
                datasets: [{
                    label: 'Cantidad de Operaciones',
                    data: Object.values(methodsDataRaw),
                    backgroundColor: '#3B82F6',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { precision: 0 }
                    }
                }
            }
        });
    }
});