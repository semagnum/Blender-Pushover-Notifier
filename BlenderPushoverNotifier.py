bl_info = {
    "name": "Blender Pushover Notifier",
    "author": "Kai Gulliksen",
    "version": (1, 2),
    "blender": (2, 80, 0),
    "location": "Properties > Render Properties > Blender Pushover Notifier",
    "description": "Sends a Pushover notification when a render is complete.",
    "category": "Render",
}

import bpy
import urllib.request
import urllib.parse
import threading  # <---  Added for non-blocking notifications

# ---  This function now returns success/failure for the test operator
def send_pushover_notification(user_key, api_token, message):
    """
    Sends a notification via the Pushover API.
    Returns (True, "Success message") or (False, "Error message")
    """
    if not user_key or not api_token:
        error_msg = "User Key or API Token not set."
        print(f"Pushover Notifier: {error_msg}")
        return (False, error_msg)

    url = "https://api.pushover.net/1/messages.json"
    data = {
        'token': api_token,
        'user': user_key,
        'message': message,
    }

    try:
        data = urllib.parse.urlencode(data).encode('utf-8')
        req = urllib.request.Request(url, data)
        urllib.request.urlopen(req)
        print("Pushover Notifier: Notification sent successfully.")
        return (True, "Notification sent successfully!")
    except Exception as e:
        error_msg = f"Failed to send notification. Error: {e}"
        print(f"Pushover Notifier: {error_msg}")
        return (False, str(error_msg))

@bpy.app.handlers.persistent
def render_complete_handler(scene):
    """
    This function is called when the render is complete.
    It now runs the notification in a separate thread.
    """
    pushover_props = scene.pushover_notifier
    
    if not pushover_props.is_enabled:
        print("Pushover Notifier: Disabled, notification not sent.")
        return
    if not bpy.app.online_access:
        print("Pushover Notifier: Blender is running in offline mode.")
        return

    blend_file_name = bpy.path.basename(bpy.context.blend_data.filepath)
    if not blend_file_name:
        blend_file_name = "Unsaved File"

    # <---  Use the customizable message format
    try:
        message = pushover_props.message_format.format(file=blend_file_name)
    except KeyError as e:
        # Fallback in case user formats the string wrong
        print(f"Pushover Notifier: Error formatting message. Invalid key: {e}")
        message = f"Blender render finished for: {blend_file_name} (Message format error)"

    # <---  Run the notification in a thread to avoid freezing Blender
    user_key = pushover_props.user_key
    api_token = pushover_props.api_token
    
    thread = threading.Thread(target=send_pushover_notification, args=(user_key, api_token, message))
    thread.start()

class PushoverNotifierProperties(bpy.types.PropertyGroup):
    is_enabled: bpy.props.BoolProperty(
        name="Enable Notifier",
        description="Enable or disable Pushover notifications",
        default=True,
    ) # type: ignore
    
    user_key: bpy.props.StringProperty(
        name="User Key",
        description="Your Pushover User Key",
        default="",
        subtype='PASSWORD',  # <--- Masks the input
    ) # type: ignore
    
    api_token: bpy.props.StringProperty(
        name="API Token/Key",
        description="Your Pushover Application API Token",
        default="",
        subtype='PASSWORD',  # <---  Masks the input
    ) # type: ignore

    # <---  Added customizable message property
    message_format: bpy.props.StringProperty(
        name="Message Format",
        description="The notification message. Use {file} for the .blend file name",
        default="Blender render finished for: {file}",
    ) # type: ignore

# <---  Operator class for the "Test" button
class PUSHOVER_OT_TestNotification(bpy.types.Operator):
    """Sends a test notification to check credentials"""
    bl_idname = "pushover.test_notification"
    bl_label = "Send Test Notification"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if bpy.app.online_access:
            return True
        
        cls.poll_message_set('Blender is running in offline mode')
        return False

    def execute(self, context):
        props = context.scene.pushover_notifier
        message = "This is a test notification from the Blender Pushover Addon."
        
        # We can call this directly (and block) because the user
        # clicked the button and expects to wait for a result.
        success, report_message = send_pushover_notification(props.user_key, props.api_token, message)

        if success:
            self.report({'INFO'}, report_message)
        else:
            self.report({'ERROR'}, report_message)
            
        return {'FINISHED'}

class RENDER_PT_PushoverNotifierPanel(bpy.types.Panel):
    """Creates a Panel in the Render properties window"""
    bl_label = "Pushover Notifier"
    bl_idname = "RENDER_PT_pushover_notifier"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"

    def draw(self, context):
        layout = self.layout
        pushover_props = context.scene.pushover_notifier

        col = layout.column()
        col.prop(pushover_props, "is_enabled")
        
        sub = col.column()
        sub.active = pushover_props.is_enabled
        sub.prop(pushover_props, "user_key")
        sub.prop(pushover_props, "api_token")
        sub.prop(pushover_props, "message_format") # <--- NEW: Added to UI
        
        # <---  Added operator button to UI
        sub.operator(PUSHOVER_OT_TestNotification.bl_idname, icon='PLAY')

# ---  Added the new Operator to the classes list
classes = (
    PushoverNotifierProperties,
    PUSHOVER_OT_TestNotification,
    RENDER_PT_PushoverNotifierPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.pushover_notifier = bpy.props.PointerProperty(type=PushoverNotifierProperties)
    if render_complete_handler not in bpy.app.handlers.render_complete:
        bpy.app.handlers.render_complete.append(render_complete_handler)

def unregister():
    if render_complete_handler in bpy.app.handlers.render_complete:
        bpy.app.handlers.render_complete.remove(render_complete_handler)
    del bpy.types.Scene.pushover_notifier
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()