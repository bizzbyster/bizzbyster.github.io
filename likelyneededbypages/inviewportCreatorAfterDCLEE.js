function sleep(milliseconds){
    var start = new Date().getTime();
    var keep_looping = true;
    while (keep_looping) {
      if ((new Date().getTime() - start)> milliseconds) {
        keep_looping = false;
      }
    }
}
(function() {
    'use strict';
    sleep(1500);
    callToDateToGenerateBreadcrumb();
})();
