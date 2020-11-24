const Charts = function () {
    let PeekTimesBar,
        SexAgeBar,
        CountryDoughnut,
        TotalMembers,
        NewMembers,
        ActiveMembers,
        VideoSessions,
        NewGroups;

    const init = function () {
        FilterChart.init('.org-chart-form .dropdown-item');

        PeekTimesBar = PeekTimesBarChart.init('#visits');
        SexAgeBar = SexAgeBarChart.init('#sex_age');
        CountryDoughnut = CountryDoughnutChart.init('#country');

        TotalMembersChart.init('#total_members');
        NewMembersChart.init('#new_members');
        ActiveMembersChart.init('#active_members');
        VideoSessionsChart.init('#video_sessions');
        NewGroupsChart.init('#new_groups');
    };

    const FilterChart = function () {
        let $toggle;

        const init = function (selector) {
            $toggle = $(selector);
            $toggle.on('click', onClick);
        };

        const onClick = function (event) {
            event.preventDefault();

            const duration = $(this).attr('href');
            const $form = $(this).closest('form');
            let $wrapper = $(this).closest('.card').find('.card-body');

            if (!$wrapper.length) {
                $wrapper = $(this).closest('.row');
            }
            const chart_id = $wrapper.find('canvas')[0].id;

            $(this).parent().find('a').removeClass('disabled');
            $(this).addClass('disabled');
            $(this).closest('.dropdown').find('span').text('By ' + duration);

            $form.find('[name="chart_id"]').attr('value', chart_id);
            $form.find('[name="duration"]').attr('value', duration);

            $wrapper.css('opacity', '.5');
            $.post($form.attr('action'), $form.serialize(), function (response) {
                $wrapper.removeAttr('style');

                if (chart_id === 'country') {
                    CountryDoughnut.data.labels = response.labels;
                    CountryDoughnut.data.datasets[0].data = response.data;
                    CountryDoughnut.update();
                } else if (chart_id === 'sex_age') {
                    SexAgeBar.data.labels = response.labels;

                    SexAgeBar.data.datasets[0].data = response.data[0];
                    SexAgeBar.data.datasets[0].label = 'Men ' + response.total[0] + '%';

                    SexAgeBar.data.datasets[1].data = response.data[1];
                    SexAgeBar.data.datasets[1].label = 'Women ' + response.total[1] + '%';

                    SexAgeBar.update();
                } else if (chart_id === 'visits') {
                    PeekTimesBar.data.labels = response.labels;
                    PeekTimesBar.data.datasets[0].data = response.data[0];
                    PeekTimesBar.data.datasets[1].data = response.data[1];
                    PeekTimesBar.update();
                } /*else if (chart_id === 'total_members') {
                    TotalMembers.data.labels = response.labels;
                    TotalMembers.data.datasets[0].data = response.dataset;
                    TotalMembers.update();
                    $wrapper.find('.total').html(response.total);
                }*/ else if (chart_id === 'new_members') {
                    NewMembers.data.labels = response.labels;
                    NewMembers.data.datasets[0].data = response.data;
                    NewMembers.update();

                    $wrapper.find('.total').html(response.total);
                } else if (chart_id === 'new_groups') {
                    NewGroups.data.labels = response.labels;
                    NewGroups.data.datasets[0].data = response.data;
                    NewGroups.update();

                    $wrapper.find('.total').html(response.total);
                } else {
                    console.warn(response);
                }
            });
        };

        return {
            init: init
        }
    }();

    const PeekTimesBarChart = function () {
        let $chart;

        const init = function (selector) {
            $chart = $(selector);

            $('#visits_toggle').on('click', onClick);

            return new Chart($chart, {
                type: 'bar',
                data: {
                    'datasets': [{
                        data: $chart.data('am'),
                        backgroundColor: '#314471'
                    }, {
                        data: $chart.data('pm'),
                        backgroundColor: '#314471',
                        hidden: true
                    }],
                    'labels': $chart.data('labels')
                },
                options: {
                    'legend': {display: false},
                    'scales': {
                        xAxes: [], yAxes: [{
                            ticks: {
                                min: 0,
                                beginAtZero: true,
                                callback: function (value, index, values) {
                                    if (Math.floor(value) === value) {
                                        return value;
                                    }
                                }
                            }
                        }]
                    }
                }
            });
        };

        const onClick = function (event) {
            event.preventDefault();
            const text = $(this).text();

            if (text === 'AM') {
                $(this).text('PM');
                PeekTimesBar.data.datasets[0].hidden = true;
                PeekTimesBar.data.datasets[1].hidden = null;
                PeekTimesBar.update();
            } else {
                $(this).text('AM');
                PeekTimesBar.data.datasets[0].hidden = null;
                PeekTimesBar.data.datasets[1].hidden = true;
                PeekTimesBar.update();
            }
        };

        return {
            init: init
        }
    }();

    const SexAgeBarChart = function () {
        let $chart;

        const init = function (selector) {
            $chart = $(selector);

            return new Chart($chart, {
                type: 'bar',
                data: {
                    'datasets': [{
                        data: $chart.data('men'),
                        backgroundColor: '#314471',
                        label: 'Men ' + $chart.data('men-total') + '%'
                    }, {
                        data: $chart.data('women'),
                        backgroundColor: '#8691ac',
                        label: 'Women ' + $chart.data('women-total') + '%'
                    }],
                    'labels': $chart.data('labels')
                },
                options: {
                    'legend': {
                        position: 'top',
                        labels: {
                            'boxWidth': 13,
                            'fontColor': '#5d5d5d',
                            'fontFamily': 'Montserrat',
                            'usePointStyle': true,
                            'padding': 30
                        }
                    },
                    'scales': {
                        xAxes: [], yAxes: [{
                            ticks: {
                                min: 0,
                                beginAtZero: true,
                                callback: function (value, index, values) {
                                    if (Math.floor(value) === value) {
                                        return value;
                                    }
                                }
                            }
                        }]
                    }
                }
            });
        };

        return {
            init: init
        }
    }();

    const CountryDoughnutChart = function () {
        let $chart;

        const init = function (selector) {
            $chart = $(selector);

            return new Chart($chart, {
                type: 'doughnut',
                data: {
                    'datasets': [{
                        data: $chart.data('set'),
                        backgroundColor: ['#547eec', '#5ab8eb', '#949dbf', '#343f61', '#785bc2', '#84ceea'],
                        borderWidth: 0
                    }],
                    'labels': $chart.data('labels')
                },
                options: {
                    'legend': {
                        position: 'right',
                        labels: {
                            'boxWidth': 13,
                            'fontColor': '#5d5d5d',
                            'fontFamily': 'Montserrat',
                            'usePointStyle': true,
                            'padding': 30
                        }
                    }
                }
            });
        };

        return {
            init: init
        }
    }();

    const TotalMembersChart = function () {
        let $chart;

        const init = function (selector) {
            $chart = $(selector);

            options.scales.yAxes[0].ticks.max = $chart.data('max');

            TotalMembers = new Chart($chart, {
                type: 'line',
                data: {
                    'labels': $chart.data('labels'),
                    'datasets': [{
                        data: $chart.data('set'),
                        fill: 'origin',
                        borderColor: '#314471',
                        borderWidth: 2,
                        backgroundColor: '#f7f7f7'
                    }]
                },
                options: options
            });
        };

        return {
            init: init
        }
    }();

    const NewMembersChart = function () {
        let $chart;

        const init = function (selector) {
            $chart = $(selector);

            options.scales.yAxes[0].ticks.max = $chart.data('max');

            NewMembers = new Chart($chart, {
                type: 'line',
                data: {
                    'labels': $chart.data('labels'),
                    'datasets': [{
                        data: $chart.data('set'),
                        fill: 'origin',
                        borderColor: '#314471',
                        borderWidth: 2,
                        backgroundColor: '#f7f7f7'
                    }]
                },
                options: options
            });
        };

        return {
            init: init
        }
    }();

    const ActiveMembersChart = function () {
        let $chart;

        const init = function (selector) {
            $chart = $(selector);

            ActiveMembers = new Chart($chart, {
                type: 'line',
                data: {
                    'labels': $chart.data('labels'),
                    'datasets': [{
                        data: $chart.data('set'),
                        fill: 'origin',
                        borderColor: '#314471',
                        borderWidth: 2,
                        backgroundColor: '#f7f7f7'
                    }]
                },
                options: options
            });
        };

        return {
            init: init
        }
    }();

    const VideoSessionsChart = function () {
        let $chart;

        const init = function (selector) {
            $chart = $(selector);

            VideoSessions = new Chart($chart, {
                type: 'line',
                data: {
                    'labels': $chart.data('labels'),
                    'datasets': [{
                        data: $chart.data('set'),
                        fill: 'origin',
                        borderColor: '#314471',
                        borderWidth: 2,
                        backgroundColor: '#f7f7f7'
                    }]
                },
                options: options
            });
        };

        return {
            init: init
        }
    }();

    const NewGroupsChart = function () {
        let $chart;

        const init = function (selector) {
            $chart = $(selector);

            options.scales.yAxes[0].ticks.max = $chart.data('max');

            NewGroups = new Chart($chart, {
                type: 'line',
                data: {
                    'labels': $chart.data('labels'),
                    'datasets': [{
                        data: $chart.data('set'),
                        fill: 'origin',
                        borderColor: '#314471',
                        borderWidth: 2,
                        backgroundColor: '#f7f7f7'
                    }]
                },
                options: options
            });
        };

        return {
            init: init
        }
    }();

    const options = {
        'responsive': true,
        'legend': {display: false},
        'scales': {
            xAxes: [{display: false}], yAxes: [{
                display: false,
                ticks: {
                    beginAtZero: true, min: 0
                }
            }]
        },
        'elements': {
            point: {
                'radius': 1,
                'hoverRadius': 1
            }
        },
        tooltips: {
            enabled: false
        },
        bezierCurve: true,
        cubicInterpolationMode: 'monotone'
    };

    return {
        init: init
    }
}();

export {Charts};
