"MISC Methods"

import os


HTML_HEADER = """
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
    .collapsible {
        background-color: #777;
        color: white;
        cursor: pointer;
        padding: 10px;
        width: 50%;
        border: none;
        text-align: left;
        outline: none;
        font-size: 13px;
    }
    .active, .collapsible:hover {
        background-color: #555;
    }
    .content {
        padding: 0 18px;
        display: none;
        overflow: auto;
        background-color: #f1f1f1;
    }
    .collapsible:after {
        content: "+";
        color: white;
        font-weight: bold;
        float: right;
        margin-left: 5px;
    }
    .active:after {
        content: "-";
    }
    </style>
    </head>
    <body>
    <div>
    <p></p>
    """


HTML_SCRIPT = """
        <div>
        <script>
        var coll = document.getElementsByClassName("collapsible");
        var i;
        for (i = 0; i < coll.length; i++) {
        coll[i].addEventListener("click", function() {
            this.classList.toggle("active");
            var content = this.nextElementSibling;
            if (content.style.display === "block") {
            content.style.display = "none";
            } else {
            content.style.display = "block";
            }
        });
        }
        </script></body></html>
        """


def create_dir(input_dir):
    """
    Description: Create the given directory path
    Input: <str>
    Output: None
    """
    try:
        os.mkdir(input_dir)
    except FileExistsError:
        pass


def format_wk(wk_no_format):
    "Format the timetuple into a 2 digit string"
    wk_formatted = ""
    if len(str(wk_no_format)) == 2:
        wk_formatted = wk_no_format
    elif len(str(wk_no_format)) == 1:
        wk_formatted = f"0{wk_no_format}"
    return wk_formatted


def format_doy(doy_no_format):
    "Format the timetuple into a 3 digit string"
    if len(doy_no_format) == 3:
        doy_formatted = doy_no_format
    elif len(doy_no_format) == 2:
        doy_formatted = f"0{doy_no_format}"
    elif len(doy_no_format) == 1:
        doy_formatted = f"00{doy_no_format}"
    return doy_formatted
