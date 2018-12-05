// (function () {
    // Editable list
    var editableList = Sortable.create(editable, {
        group: "urls",
        animation: 150,
        filter: '.js-remove',
        onFilter: function (evt) {
            evt.item.parentNode.removeChild(evt.item);
            let selurls = $('li').children('input').map(function(){return $(this).val();}).get(); //get array of values of all inputs in list
            localStorage.setItem('selurls', selurls.toString());
        },
        onUpdate: function(){ //user has changed order in list
            let selurls = $('li').children('input').map(function(){return $(this).val();}).get(); //get array of values of all inputs in list
            localStorage.setItem('selurls', selurls.toString());
        }
    });

    $('.meta').change(function(event){ //one of the meta input fields is changed
        var metas = $('.meta').map(function(){return $(this).val();}).get();
        localStorage.setItem('metas', metas.toString());
    });

    if (localStorage.metas) { //fill list with urls in localstorage
        var metas = localStorage.metas.split(","); //array of earlier given meta-inputs
        $('#tit').val(metas[0]);
        $('#des').val(metas[1]);
        $('#aut').val(metas[2]);
        $('#lan').val(metas[3]);
        $('#color-input').val(metas[4]);
    }

    if (localStorage.selurls) { //fill list with urls in localstorage
        var selurls = localStorage.selurls.split(","); //array of earlier selected urls
        for (i in selurls){
            addurltolist(selurls[i]);
        }
    }


    function storeSelection(elem, str) {
        var sel;
        if (localStorage.getItem(str)) { // there are earlier selected urls
            sel = localStorage.getItem(str).split(","); // set in array
            if (sel.indexOf(elem) < 0) { //if not already existing
                sel.push(elem); //add to array
            }
        } else { //no earlier selected countries
            sel = [elem];
        }
        localStorage.setItem(str, sel.toString());
    }

// })();

function addurltolist(url){
    let length = $("#editable li").length
    let elem = '<li class="w3-display-container"><input name="url' + length + '" value="' + url + 
        '" type="url" size="100%" class="w3-border-0 urls">' +
        '<span class="js-remove w3-button w3-transparent w3-display-right">&times;</span></li>';
    console.log('elem: ' + elem)
    $('#editable').append(elem);
    storeSelection(url, "selurls");
}

function validateForm() {
    let length = document.getElementById("editable").getElementsByTagName("li").length;
    if (length < 1) {
        Ply.dialog("alert", {
            title: "Cannot make book",
            text: "Please give at least 1 webpage url"
        });
        return false;
    } else {
        return true;
    }
}

window.onbeforeunload = function(){
    window.scrollTo(0, 0); //scroll to top
}



$(document).ready(function () {
    namespace = '/test';
    var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port + namespace);

    $("#popup01").hide();

    $('#about_btn').on('click', function () {
        // $('#popup_textarea').hide();
        var d = new Date();
        var yyyy = d.getFullYear();
        // $("#favicon").removeClass("favicon2");
        // var hd = _lg.About2;
        var hd = 'About';
        var msg = "<p>" + 'Message' + "</p>";
        msg += "<p><a href='https://radios2s.scriptel.nl' target='_blank'>radios2s.scriptel.nl</a></p>";
        // showAbout(hd,msg);
        $("#popupheader").html(hd);
        $("#popupmessage").html(msg);
        $("#popup_textarea, #popup_cancel").hide();
        $("#popup_ok").show();
        $("#popup01").fadeIn();
    });

    $('#addurls').click(function(){
        let hd = 'Add one or more urls';
        let msg = 'Copy here one or more urls. Each url should be on a new line.';
        let label = 'Urls';
        $("#popupheader").html(hd);
        $("#popupmessage").html(msg);
        $("#popup_textarea_label").html(label);
        $("#popup_textarea_text").val('');
        $("#popup_textarea, #popup_cancel").show();
        $("#popup01").show();
        $("#popup_textarea_text").focus();
    });

    $('#clearurls').click(function(){
        $('#editable').empty();
        localStorage.setItem('selurls', '');
    });

    $('#closepopup01, #popup_cancel').click(function () { //close popup
        $("#popup01").hide();
    });
    // ########################################
    $('#popup_ok').click(function(){ 
        let txt = $('#popup_textarea_text').val();
        txt = $.trim(txt);
        // var lines = $('#popup_textarea_text').val().split('\n');
        var lines = txt.split('\n');
        for(var i = 0;i < lines.length;i++){
            //check if url is url #####
            if (lines[i].length > 0) {
                addurltolist(lines[i]);
            }
        }
        $("#popup01").hide();
    });


    socket.on('connect', function () {
        console.log('Start making book')
    });
    $('#makebook').click(function(){
        if (validateForm()){
            let urls = $('.urls').map(function(){return $(this).val();}).get();
            let datas = $('.data').map(function(){return $(this).val();}).get();
            datas.unshift(datas.length);
            console.log('datas: ' + datas.toString());
            datas = $.merge(datas, urls);
            console.log('datas: ' + datas.toString());
            socket.emit('make_book', {
                data: datas.toString()
            });
            window.scrollBy(0, 1000);
        }
    });
    socket.on('my_response', function (msg) {
        $('#log').append($('<div/>').text(msg.data).html() + '\n');
        let $textarea = $('#log');
        $textarea.scrollTop($textarea[0].scrollHeight);    
    });
    socket.on('book_finished', function (msg) {
        window.location.href = msg.data //download file
    });
});