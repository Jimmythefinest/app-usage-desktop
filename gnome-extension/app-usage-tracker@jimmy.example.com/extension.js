import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

const DBUS_INTERFACE = `
<node>
  <interface name="org.gnome.Shell.Extensions.AppUsage">
    <method name="GetActiveWindow">
      <arg type="s" name="app_name" direction="out"/>
      <arg type="s" name="window_title" direction="out"/>
      <arg type="i" name="pid" direction="out"/>
      <arg type="i" name="window_id" direction="out"/>
    </method>
  </interface>
</node>`;

export default class AppUsageTrackerExtension {
    constructor() {
        this._dbusId = 0;
    }

    enable() {
        this._nodeInfo = Gio.DBusNodeInfo.new_for_xml(DBUS_INTERFACE);
        this._dbusId = Gio.DBus.session.register_object(
            '/org/gnome/Shell/Extensions/AppUsage',
            this._nodeInfo.interfaces[0],
            this._handleMethodCall.bind(this),
            null, null
        );
    }

    disable() {
        if (this._dbusId) {
            Gio.DBus.session.unregister_object(this._dbusId);
            this._dbusId = 0;
        }
    }

    _handleMethodCall(connection, sender, objectPath, interfaceName, methodName, parameters, invocation) {
        if (methodName === 'GetActiveWindow') {
            let focusWindow = global.display.get_focus_window();
            let appName = "";
            let title = "";
            let pid = 0;
            let windowId = 0;

            if (focusWindow) {
                title = focusWindow.get_title() || "";
                pid = focusWindow.get_pid() || 0;
                // get_id() might not exist on all Mutter versions, use hash if missing
                windowId = focusWindow.get_id ? focusWindow.get_id() : focusWindow.hash();
                
                let tracker = global.window_manager.get_window_tracker();
                let app = tracker.get_window_app(focusWindow);
                if (app) {
                    appName = app.get_name() || app.get_id() || "";
                }
            }

            invocation.return_value(new GLib.Variant('(ssii)', [appName, title, pid, windowId]));
        }
    }
}
