// TODO: Refactor methods

const Timezone = function () {
    const init = function (value) {
        let self = {
            init: function (cities, formatName) {
                this.cities = [];
                this.formatName = formatName;

                for (let key in cities) {
                    this.cities.push({
                        name: cities[key],
                        offset: moment.tz(cities[key]).format('Z')
                    });
                }

                this.cities.sort(function (a, b) {
                    return parseInt(a.offset.replace(':', ''), 10) - parseInt(b.offset.replace(':', ''), 10);
                });

                this.html = this.getHTMLOptions();
                this.currentTimezone = this.getCurrentTimezoneKey();
            },
            getHTMLOptions: function () {
                let html = '';
                const offset = 0;
                let i, c = this.cities.length, city;

                for (i = 0; i < c; i++) {
                    city = this.cities[i];
                    html += $('<option />', {
                        'data-offset': city.offset,
                        'value': city.name,
                        'text': '(GMT ' + city.offset + ') ' + this.formatName(city.name)
                    }).prop('outerHTML');
                }

                return html;
            },
            addNames: function (select) {
                return $(select).empty().append($(this.html));
            },
            selectCurrentTz: function (select) {
                let current_tz = value ? value : moment.tz.guess();
                let selector = 'option[value="' + current_tz + '"]';
                const match = $(select).find(selector);

                if (match.length) {
                    $(select).val(match.val());
                }

                return $(select);
            },
            getCurrentTimezoneKey: function () {
                return moment().format('Z');
            },
            getCurrentOffset: function () {
                return parseInt(this.currentTimezone, 10);
            }
        };

        $.fn.timezones = function (opts) {
            if (typeof opts === 'string') {
                return self[opts].apply(self, Array.prototype.slice.call(arguments));
            }

            opts = $.extend({}, $.fn.timezones.defaults, opts);

            if (opts.tz.zones.length !== 0) {
                moment.tz.load(opts.tz);
            }

            if (!opts.formatName || typeof opts.formatName !== 'function') {
                opts.formatName = function (str) {
                    return str;
                };
            }

            self.init(moment.tz.names(), opts.formatName);

            return this.each(function () {
                self.addNames(this);
                self.selectCurrentTz(this);
                return this;
            });
        };

        $.fn.timezones.defaults = {
            tz: {
                zones: []
            }
        };

        $('.timezonepicker').timezones();
    };

    return {
        init: init
    }
}();

export {Timezone};
