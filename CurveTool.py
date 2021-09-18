bl_info = {
    "name": "CurveTool",
    "blender": (2, 93, 4),
    "category": "Curve"
}

import bpy
import mathutils
import copy

def normalizeAndSetDefaultControlHandlesOfBezierCurve(a_curve):
    if len(a_curve.splines) < 1: return -1
    firstSpline = a_curve.splines[0]
    if firstSpline.type == 'BEZIER':
        numberOfBezierPoints = len(firstSpline.bezier_points)        
        if numberOfBezierPoints > 1:
            
            for i in range(numberOfBezierPoints-1):
                currentPoint = firstSpline.bezier_points[i]
                currentPointCoordinates = firstSpline.bezier_points[i].co
                currentPointVec = mathutils.Vector(currentPointCoordinates)
                nextPointVec = mathutils.Vector(firstSpline.bezier_points[i+1].co)
                vectorFromCurrentPointToNext = nextPointVec - currentPointVec
                normalizedVec = 1.0 * vectorFromCurrentPointToNext.normalized()
                currentPoint.handle_right = currentPointVec + normalizedVec
                currentPoint.handle_left = currentPointVec - normalizedVec
            
            lastPoint = firstSpline.bezier_points[numberOfBezierPoints-1]
            lastPointCoordinates = lastPoint.co
            lastPointVec = mathutils.Vector(lastPointCoordinates)
            previousPointVec = mathutils.Vector(firstSpline.bezier_points[numberOfBezierPoints-2].co)
 
            vectorFromPreviousPointToLast = lastPointVec - previousPointVec
            normalizedVec = 1.0 * vectorFromPreviousPointToLast.normalized()
            lastPoint.handle_right = lastPointVec + normalizedVec
            lastPoint.handle_left = lastPointVec - normalizedVec
            
        else:
            print("No bezier points in curve. Nothing done.")
            return -1


# points: list of 3 length vectors ex: [(x1, y1, z1), (x2, y2, z2), ...]
def createCurveBetweenPoints(user_points, u_bevel_depth=0.5, u_bevel_resolution=2, curveType="BEZIER"):
        # Add a curve to the blend file's data
        curve = bpy.data.curves.new('curve_root', 'CURVE')

        # Curves start with 0 splines

        # Add a spline to the curve (a spline is a single connected curve. i.e. one curve can have several separate unconnected splines)
        curve.splines.new(type=curveType)

        # Set the curve's dimension type to '3D' so that it can be moved in the z-axis
        curve.dimensions = '3D'

        # Set the bevel depth of the curve so that it has thickness
        curve.bevel_depth = u_bevel_depth
        
        # Set the bevel resolution (the roundness) (between 0 and 32)
        curve.bevel_resolution = u_bevel_resolution

        # Give the curve a full circular bevel geometry
        curve.fill_mode = 'FULL'
        
        if curveType == 'POLY':
            # Add a point to the curve's first spline for every given point (-1 because every spline starts with one point) (the spline now has len(points) points)
            curve.splines[0].points.add(count=len(user_points)-1)

            # set the coordinates of the points to the given arguments
            indexCounter = 0
            for p in curve.splines[0].points:
                user_point = user_points[indexCounter]
                p.co = (user_point[0], user_point[1], user_point[2], 0)
                indexCounter = indexCounter + 1
            
            
        elif curveType == 'BEZIER':
            # Add a point to the curve's first spline for every given point (-1 because every spline starts with one point) (the spline now has len(points) points)
            curve.splines[0].bezier_points.add(count=len(user_points)-1)
            
            # set the coordinates of the points to the given arguments
            indexCounter = 0
            for p in curve.splines[0].bezier_points:
                user_point = user_points[indexCounter]
                p.co = (user_point[0], user_point[1], user_point[2])
                # set the handle types to ALIGNED, default is FREE
                p.handle_left_type = 'ALIGNED'
                p.handle_right_type = 'ALIGNED'
                indexCounter = indexCounter + 1
                
            normalizeAndSetDefaultControlHandlesOfBezierCurve(curve)
            
        # NOTE: bpy.data.curves is an instance of BlendeDataCurves which is a collection of bpy.types.Curve(ID) objects

        # Initialize an object out of the curve
        curve_obj = bpy.data.objects.new('curve', curve)

        # Link the newly created curve object to the active scene in blender so that it can be seen
        bpy.context.view_layer.active_layer_collection.collection.objects.link(curve_obj)

        return curve


class CurveTool(bpy.types.Operator):
    """Generate Curve on Surfaces of Mouse Clicks"""
    bl_idname = "curve.jcurve_tool"
    bl_label = "CurveTool"
    # To get and undo panel on the left hand side panel for the settings of the operator
    bl_options = {'REGISTER', 'UNDO'}
    
    # Undo panel fields for the user to set bevel depth and bevel resolution
    bevel_depth_setting: bpy.props.FloatProperty(name='Bevel Depth', min=0, default=0.5)
    bevel_resolution_setting: bpy.props.IntProperty(name='Bevel Resolution', min=1, max=32, default=2)
    curve_type_setting: bpy.props.EnumProperty(items=[('BEZIER', 'BEZIER', 'BEZIER'), ('POLY', 'POLY', 'POLY')], name='Curve Type', description='The curve type to use')
    

    # Called first, before this operator is ran, poll is called.
    # If the area the user is in when activating the operator is not the 3dview, then the operator is not started, otherwise it is.
    @classmethod
    def poll(cls, context):
        return context.area.type == "VIEW_3D"

    # Called when the user makes changes to the operator properties in the UNDO panel
    def execute(self, context):
        createCurveBetweenPoints(self.clickPositions3d, self.bevel_depth_setting, self.bevel_resolution_setting, curveType=self.curve_type_setting)
        return {'FINISHED'}


    # Called whenever an event happens (click, key press, move move)
    # - every left click on a surface is recorded as the next point to be created for the curve
    # - on a right click or enter press, the modal mode is exited
    # - any other event is ignored by returning 'PASS_THROUGH' allowing the user to still use functionality with these other events (like navigate the 3dview)
    def modal(self, context, event):
        # Exiting modal operator
        if event.type == 'RIGHTMOUSE' or event.type == 'RET':
            
            if len(self.clickPositions3d) > 1:
                createCurveBetweenPoints(self.clickPositions3d)
            else:
                print("Potential error. Number of click positions for curve generation is less than 2.")
                self.report({'ERROR'}, "Number of click positions for curve generation is less than 2.")
            
            print("Exiting CurveTool Modal Operator.")
            return {'FINISHED'}
        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            
            # set 3d cursor position to 2d click 
            bpy.ops.view3d.cursor3d('INVOKE_DEFAULT')
            clickPosition3d = copy.deepcopy(context.scene.cursor.location)
            # store the 3d click position so it can be used later as one of the points to generate the curve
            self.clickPositions3d.append(clickPosition3d)
            
            self.numberOfClicksCurrently = self.numberOfClicksCurrently + 1
            return {'RUNNING_MODAL'}
        else:
            return {'PASS_THROUGH'}
    
    def invoke(self, context, event):
        self.numberOfClicksCurrently = 0
        self.clickPositions3d = []
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


def menu_func(self, context):
    self.layout.operator(CurveTool.bl_idname)


def register():
    bpy.utils.register_class(CurveTool)
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    bpy.utils.unregister_class(CurveTool)

# For Testing Operator without having to install it
#if __name__ == "__main__":
#    register()