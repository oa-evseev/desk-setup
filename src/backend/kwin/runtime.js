//
// desk-setup KWin one-shot runtime
//

"use strict";


const REQUEST = __REQUEST_JSON__;

const REPLY_SERVICE = __REPLY_SERVICE__;
const REPLY_PATH = __REPLY_PATH__;
const REPLY_INTERFACE = __REPLY_INTERFACE__;


function toText(value) {

    if (
        value === undefined
        || value === null
    ) {
        return "";
    }

    return String(value);
}


function errorMessage(error) {

    if (
        error === undefined
        || error === null
    ) {
        return "Unknown JavaScript error";
    }

    if (error.message) {
        return String(error.message);
    }

    return String(error);
}


function errorStack(error) {

    if (
        error
        && error.stack
    ) {
        return String(error.stack);
    }

    return "";
}


function success(result) {

    return {
        ok: true,
        result:
        result === undefined
        ? null
        : result,
    };
}


function failure(error) {

    return {
        ok: false,
        error: errorMessage(error),
        stack: errorStack(error),
    };
}


function sendReply(response) {

    let payload;

    try {

        payload = JSON.stringify(response);

    } catch (error) {

        payload = JSON.stringify({
            ok: false,
            error:
            "Could not serialise KWin response: "
            + errorMessage(error),
                                 stack: errorStack(error),
        });
    }

    callDBus(
        REPLY_SERVICE,
        REPLY_PATH,
        REPLY_INTERFACE,
        "Reply",
        payload,
        function () {
        },
    );
}


function windowList() {

    if (
        typeof workspace.windowList
        === "function"
    ) {
        return workspace.windowList();
    }

    if (workspace.stackingOrder) {
        return workspace.stackingOrder;
    }

    return [];
}


function outputList() {

    if (workspace.outputs) {
        return workspace.outputs;
    }

    if (workspace.screens) {
        return workspace.screens;
    }

    return [];
}


function getWindow(handle) {

    const expected = String(handle);
    const windows = windowList();

    for (const window of windows) {

        if (
            String(window.internalId)
            === expected
        ) {
            return window;
        }
    }

    return null;
}


function geometryOf(window) {

    const geometry = window.frameGeometry;

    if (!geometry) {
        return null;
    }

    return {
        x: Number(geometry.x),
        y: Number(geometry.y),
        width: Number(geometry.width),
        height: Number(geometry.height),
    };
}


function desktopOf(window) {

    if (
        window.desktop !== undefined
        && window.desktop !== null
    ) {
        const desktop = window.desktop;

        if (
            typeof desktop === "number"
            || typeof desktop === "string"
        ) {
            return desktop;
        }

        if (
            desktop.x11DesktopNumber
            !== undefined
        ) {
            return Number(
                desktop.x11DesktopNumber,
            );
        }

        if (desktop.id !== undefined) {
            return String(desktop.id);
        }
    }

    if (
        window.desktops
        && window.desktops.length > 0
    ) {
        const desktop = window.desktops[0];

        if (
            desktop.x11DesktopNumber
            !== undefined
        ) {
            return Number(
                desktop.x11DesktopNumber,
            );
        }

        if (desktop.id !== undefined) {
            return String(desktop.id);
        }
    }

    return null;
}


function listWindows() {

    const result = [];
    const windows = windowList();

    for (const window of windows) {

        const geometry = geometryOf(window);

        if (!geometry) {
            continue;
        }

        result.push({

            handle: String(
                window.internalId,
            ),

            pid: Number(window.pid),

                    title: toText(
                        window.caption,
                    ),

                    appId: toText(
                        window.resourceClass,
                    ),

                    desktop: desktopOf(window),

                    output:
                    window.output
                    ? toText(
                        window.output.name,
                    )
                    : "",

                    x: geometry.x,
                    y: geometry.y,

                    width: geometry.width,
                    height: geometry.height,
        });
    }

    return result;
}

function listOutputs() {

    const result = [];
    const outputs = outputList();

    for (const output of outputs) {

        let geometry = null;

        try {

            geometry = workspace.clientArea(
                KWin.MaximizeArea,
                output,
                workspace.currentDesktop,
            );

        } catch (error) {

            geometry = output.geometry;
        }

        if (!geometry) {
            continue;
        }

        result.push({

            name: toText(
                output.name,
            ),

            x: Number(
                geometry.x,
            ),

            y: Number(
                geometry.y,
            ),

            width: Number(
                geometry.width,
            ),

            height: Number(
                geometry.height,
            ),

            scale:
            output.scale !== undefined
            ? Number(output.scale)
            : 1,

            enabled:
            output.enabled !== undefined
            ? Boolean(output.enabled)
            : true,
        });
    }

    return result;
}


function requireNumber(
    value,
    name,
) {

    const number = Number(value);

    if (!Number.isFinite(number)) {

        throw new Error(
            "Invalid numeric parameter "
            + name
            + ": "
            + toText(value),
        );
    }

    return number;
}


function requirePositiveNumber(
    value,
    name,
) {

    const number = requireNumber(
        value,
        name,
    );

    if (number <= 0) {

        throw new Error(
            "Parameter "
            + name
            + " must be positive",
        );
    }

    return number;
}


function moveResizeWindow(
    handle,
    x,
    y,
    width,
    height,
) {

    const window = getWindow(handle);

    if (!window) {

        throw new Error(
            "KWin window was not found: "
            + toText(handle),
        );
    }

    const target = {

        x: Math.round(
            requireNumber(
                x,
                "x",
            ),
        ),

        y: Math.round(
            requireNumber(
                y,
                "y",
            ),
        ),

        width: Math.round(
            requirePositiveNumber(
                width,
                "width",
            ),
        ),

        height: Math.round(
            requirePositiveNumber(
                height,
                "height",
            ),
        ),
    };

    /*
     * KWin will not apply arbitrary frame geometry
     * while the window is fullscreen, maximised,
     * minimised or attached to a tile.
     */

    if (window.minimized) {
        window.minimized = false;
    }

    if (window.fullScreen) {
        window.fullScreen = false;
    }

    if (
        window.tile !== undefined
        && window.tile !== null
    ) {
        window.tile = null;
    }

    if (
        typeof window.setMaximize
        === "function"
    ) {
        window.setMaximize(
            false,
            false,
        );
    }

    window.frameGeometry = target;

    const actual = geometryOf(window);

    return {
        requested: target,
        actual: actual,
        output:
        window.output
        ? toText(window.output.name)
        : "",
        fullscreen: Boolean(
            window.fullScreen,
        ),
        minimized: Boolean(
            window.minimized,
        ),
        tiled:
        window.tile !== undefined
        && window.tile !== null,
    };
}


function quickTileSlot(tile) {

    const slots = {
        "left":
        "slotWindowQuickTileLeft",

        "right":
        "slotWindowQuickTileRight",

        "top":
        "slotWindowQuickTileTop",

        "bottom":
        "slotWindowQuickTileBottom",

        "top-left":
        "slotWindowQuickTileTopLeft",

        "top-right":
        "slotWindowQuickTileTopRight",

        "bottom-left":
        "slotWindowQuickTileBottomLeft",

        "bottom-right":
        "slotWindowQuickTileBottomRight",
    };

    const slot = slots[
        toText(tile)
    ];

    if (!slot) {

        throw new Error(
            "Unsupported KWin Quick Tile preset: "
            + toText(tile)
        );
    }

    return slot;
}


function quickTileWindow(
    handle,
    tile
) {

    const window = getWindow(handle);

    if (!window) {

        throw new Error(
            "KWin window was not found: "
            + toText(handle)
        );
    }

    const slot = quickTileSlot(
        tile
    );

    window.minimized = false;
    window.fullScreen = false;

    if (
        typeof window.setMaximize
        === "function"
    ) {

        window.setMaximize(
            false,
            false
        );
    }

    /*
     * moveResizeWindow() has already moved the window
     * to the intended output. Clear any previous tile
     * association before applying the requested one.
     */
    window.tile = null;

    workspace.activeWindow = window;

    const operation = workspace[slot];

    if (
        typeof operation
        !== "function"
    ) {

        throw new Error(
            "KWin workspace method is unavailable: "
            + slot
        );
    }

    operation.call(
        workspace
    );

    return window.tile !== null;
}


function activateWindow(handle) {

    const window = getWindow(handle);

    if (!window) {
        return false;
    }

    workspace.activeWindow = window;

    return true;
}


function parametersOf(request) {

    if (
        !request
        || typeof request !== "object"
    ) {
        return {};
    }

    if (
        !request.params
        || typeof request.params !== "object"
    ) {
        return {};
    }

    return request.params;
}


function dispatch(request) {

    if (
        !request
        || typeof request !== "object"
    ) {
        throw new Error(
            "Invalid KWin request",
        );
    }

    const method = toText(
        request.method,
    );

    if (!method) {
        throw new Error(
            "KWin request has no method",
        );
    }

    const params = parametersOf(
        request,
    );

    switch (method) {

        case "listWindows":

            return listWindows();


        case "listOutputs":

            return listOutputs();


        case "moveResizeWindow":

            return moveResizeWindow(

                params.handle,

                params.x,
                params.y,

                params.width,
                params.height,
            );


        case "activateWindow":

            return activateWindow(
                params.handle,
            );


        case "quickTileWindow":

            return quickTileWindow(
                params.handle,
                params.tile
            );


        default:

            throw new Error(
                "Unknown KWin method: "
                + method,
            );
    }
}

function main() {

    let response;

    try {

        response = success(
            dispatch(REQUEST),
        );

    } catch (error) {

        response = failure(error);
    }

    sendReply(response);
}


main();
