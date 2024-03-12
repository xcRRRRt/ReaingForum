$(document).ready(function () {
    const csrfToken = $('input[name="csrfmiddlewaretoken"]').val();

    let avatar_input = $("#id_avatar");
    avatar_input.addClass("form-control")

    // 中间部分的表单
    // 妈的，这才是用bootstrap打开django表单的正确方式，为什么我现在才发现
    // 妈的，前面登录的几个表单已经不敢动了呜呜呜
    $("#userinfo-form label").each(function () {
        $(this).attr("class", "form-label");    // 选择label元素
        let nextElement = $(this).next();       // 选择label的下一个元素，也就是input和textarea等元素
        nextElement.attr("class", "form-control");
        let parentElement = $(this).parent();   // 选择label的父元素
        parentElement.attr("class", "mb-3");
    });

    function remove() {
        let container = $(this).parent();
        container.remove();
    }

    // 右边部分的地址，点击添加按钮添加一个输入，点击删除按钮删除一个输入，点击保存进行保存
    let addr_container = $("#addr-container");
    addr_container.find("button").click(remove);
    $("#add-address").click(function () {
        const input = $("<input type=\"text\" class=\"form-control\" placeholder=\"输入一个新的地址\">");
        const delete_btn = $("<button class=\"btn btn-outline-danger\" type=\"button\">删除</button>");
        const addr_item_container = $("<div class=\"input-group mt-2\"></div>")
        delete_btn.click(remove);
        addr_item_container.append(input, delete_btn);
        addr_container.append(addr_item_container);
    })


    // 保存地址
    $("#save-addr").click(function () {
        let addresses = []  // 地址数组
        $("#addr-container input").map(function () {
            // 对地址进行简单预处理
            let addr = $(this).val().trim()
            if (addr.length !== 0) {
                addresses.push(addr);
            }
        })
        if (addresses.length !== 0) {
            $.ajax({
                url: "/user/save-addr/",
                type: 'post',
                headers: {
                    'X-CSRFToken': csrfToken  // Include the CSRF token in the headers
                },
                data: {
                    "addresses": addresses
                },
                success: function (res) {
                    if (res.success) {
                        const toastLive = $("#liveToast");
                        toastLive.find(".toast-header").removeClass().addClass("toast-header bg-info");
                        toastLive.find("strong").text("信息");
                        toastLive.find("small").text("");
                        toastLive.find(".toast-body").text("保存成功");
                        const toast = new bootstrap.Toast(toastLive);
                        toast.show();
                    } else {
                        const toastLive = $("#liveToast");
                        toastLive.find(".toast-header").removeClass().addClass("toast-header bg-danger");
                        toastLive.find("strong").text("信息");
                        toastLive.find("small").text("");
                        toastLive.find(".toast-body").text("保存识别");
                        const toast = new bootstrap.Toast(toastLive);
                        toast.show();
                    }
                }
            });
        }
    });
});