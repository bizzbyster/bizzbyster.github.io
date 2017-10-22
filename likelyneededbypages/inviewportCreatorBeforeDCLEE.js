(function() {
    'use strict';
    var imageNode = document.createElement('img');
    imageNode.src = 'sparrow.png?inviewport-jsloaded';
    var inviewportDiv = document.getElementById('inviewport-images');
    inviewportDiv.appendChild(imageNode);
    var scriptLoader = document.createElement('script');
    scriptLoader.type = 'application/javascript';
    scriptLoader.src = 'inviewportCreatorAfterDCLEE.js';
    document.body.appendChild(scriptLoader);
})();
