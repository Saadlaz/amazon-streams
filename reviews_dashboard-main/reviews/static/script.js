    const sentimentData = {{ sentiment_data|safe }};
    const labels = Object.keys(sentimentData);
    const values = Object.values(sentimentData);

    const ctx1 = document.getElementById('sentimentChart').getContext('2d');
    new Chart(ctx1, {
      type: 'pie',
      data: {
        labels: labels,
        datasets: [{
          label: 'Sentiment Distribution',
          data: values,
          backgroundColor: [
            '#4da6ff', // Light blue for positive
            '#cccccc', // Gray for negative
            '#e6f2ff'  // Lighter blue for neutral
          ],
          borderColor: 'white',
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'right',
            labels: {
              boxWidth: 12,
              padding: 20
            }
          }
        }
      }
    });

    
    const ctx2 = document.getElementById('timeChart').getContext('2d');
    new Chart(ctx2, {
      type: 'line',
      data: {
        labels: dates,
        datasets: [{
          label: 'Reviews per Day',
          data: counts,
          borderColor: '#4da6ff',
          backgroundColor: 'rgba(77, 166, 255, 0.1)',
          borderWidth: 2,
          pointBackgroundColor: 'white',
          pointBorderColor: '#4da6ff',
          pointRadius: 4,
          pointHoverRadius: 6,
          fill: true,
          tension: 0.3
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            grid: {
              color: '#f0f0f0'
            }
          },
          x: {
            grid: {
              display: false
            }
          }
        },
        plugins: {
          tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            cornerRadius: 4
          }
        }
      }
    });
