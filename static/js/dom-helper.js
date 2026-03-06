/**
 * Shared DOM element builder — used by meeting-picker, followup-picker,
 * and portal progress charts.
 *
 * Usage:
 *   el("div", { className: "card" }, [
 *       el("h2", null, "Title"),
 *       el("p", null, "Body text"),
 *   ]);
 *
 * @param {string} tag - HTML tag name
 * @param {Object|null} attrs - Attributes (className handled specially)
 * @param {string|Node|Array} children - Text, element, or array of both
 * @returns {HTMLElement}
 */
function el(tag, attrs, children) {
    var node = document.createElement(tag);
    if (attrs) {
        for (var k in attrs) {
            if (k === "className") { node.className = attrs[k]; }
            else { node.setAttribute(k, attrs[k]); }
        }
    }
    if (children) {
        if (typeof children === "string") {
            node.textContent = children;
        } else if (Array.isArray(children)) {
            children.forEach(function (c) {
                if (typeof c === "string") node.appendChild(document.createTextNode(c));
                else if (c) node.appendChild(c);
            });
        } else {
            node.appendChild(children);
        }
    }
    return node;
}
