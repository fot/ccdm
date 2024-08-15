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
