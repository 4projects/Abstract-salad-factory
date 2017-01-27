"use strict";

function storageAvailable(type) {
	try {
		var storage = window[type],
			x = '__storage_test__';
		storage.setItem(x, x);
		storage.removeItem(x);
		return true;
	}
	catch(e) {
		return false;
	}
}

function setMomentLocaleCalendars() {
	if (moment != null) {
		moment.updateLocale('en', {
			calendar: {
				lastDay: '[Yesterday]',
				sameDay: '[Today]',
				nextDay: '[Tomorrow]',
				lastWeek: '[last] dddd',
				nextWeek: 'dddd',
				sameElse: 'dddd, ll'
			}
		});

		moment.updateLocale('nl', {
			calendar: {
				lastDay: '[gisteren]',
				sameDay: '[vandaag]',
				nextDay: '[morgen]',
				lastWeek: '[afgelopen] dddd',
				nextWeek: 'dddd',
				sameElse: 'dddd ll'
			}
		});
	};
};
