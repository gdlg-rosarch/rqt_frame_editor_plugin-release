#!/usr/bin/env python

import copy

import rospy

from frame_editor.objects import *
from frame_editor.commands import *
from frame_editor.interface import Interface

from frame_editor.constructors_geometry import *
from frame_editor.constructors_std import *

from frame_editor.srv import *


class FrameEditor_Services(Interface):

    def __init__(self, frame_editor):

        self.editor = frame_editor

        rospy.Service("align_frame", AlignFrame, self.callback_align_frame)
        rospy.Service("edit_frame", EditFrame, self.callback_edit_frame)
        rospy.Service("get_frame", GetFrame, self.callback_get_frame)
        rospy.Service("remove_frame", RemoveFrame, self.callback_remove_frame)
        rospy.Service("set_frame", SetFrame, self.callback_set_frame)
        rospy.Service("set_parent", SetParentFrame, self.callback_set_parent_frame)
        rospy.Service("copy_frame", CopyFrame, self.callback_copy_frame)


    def callback_align_frame(self, request):
        print "> Request to align frame", request.name, "with frame", request.source_name, "mode", request.mode

        response = AlignFrameResponse()
        response.error_code = 0

        if request.name == "":
            print " Error: No name given"
            response.error_code = 1

        elif request.source_name == "":
            print " Error: No source name given"
            response.error_code = 3

        elif request.name not in self.editor.frames:
            print " Error: Frame not found:", request.name
            response.error_code = 2

        else:
            frame = self.editor.frames[request.name]

            m = request.mode
            mode = []
            if m & 1: mode.append("x")
            if m & 2: mode.append("y")
            if m & 4: mode.append("z")
            if m & 8: mode.append("a")
            if m & 16: mode.append("b")
            if m & 32: mode.append("c")

            self.editor.command(Command_AlignElement(self.editor, frame, request.source_name, mode))

        return response


    def callback_edit_frame(self, request):
        print "> Request to edit frame", request.name

        response = EditFrameResponse()
        response.error_code = 0

        if request.name == "":
            ## Reset
            self.editor.command(Command_SelectElement(self.editor, None))

        elif request.name not in self.editor.frames:
            print " Error: Frame not found:", request.name
            response.error_code = 2

        else:
            ## Set
            self.editor.command(Command_SelectElement(self.editor, self.editor.frames[request.name]))

        return response


    def callback_get_frame(self, request):
        print "> Request to get frame", request.name

        response = GetFrameResponse()
        response.error_code = 0

        if request.name == "":
            print " Error: No name given"
            response.error_code = 1

        elif request.name not in self.editor.frames:
            print " Error: Frame not found:", request.name
            response.error_code = 2

        else:
            f = self.editor.frames[request.name]
            f.print_all()
            response.name = f.name
            response.parent = f.parent
            response.pose = ToPose(f.position, f.orientation)

        return response


    def callback_remove_frame(self, request):
        print "> Request to remove frame", request.name

        response = RemoveFrameResponse()
        response.error_code = 0

        if request.name == "":
            print " Error: No name given"
            response.error_code = 1

        elif request.name not in self.editor.frames:
            print " Error: Frame not found:", request.name
            response.error_code = 2

        else:
            self.editor.command(Command_RemoveElement(self.editor, self.editor.frames[request.name]))

        return response


    def callback_set_frame(self, request):
        print "> Request to set (or add) frame", request.name, request.parent

        response = SetFrameResponse()
        response.error_code = 0

        if request.name == "":
            print " Error: No name given"
            response.error_code = 1

        else:
            if request.parent == "":
                request.parent = "world"

            f = Frame(request.name,
                      FromPoint(request.pose.position),
                      FromQuaternion(request.pose.orientation),
                      request.parent)
            self.editor.command(Command_AddElement(self.editor, f))

        return response


    def callback_set_parent_frame(self, request):
        print "> Request to set parent_frame", request.name, request.parent

        response = SetParentFrameResponse()
        response.error_code = 0

        if request.name == "":
            print " Error: No frame_name given"
            response.error_code = 1

        elif request.parent == "":
            print " Error: No parent_name given"
            response.error_code = 2

        else:
            f = self.editor.frames[request.name]
            self.editor.command(Command_SetParent(self.editor, f, request.parent, request.keep_absolute))

        return response


    def callback_copy_frame(self, request):
        print "> Request to copy frame '" + request.source_name + "' with new name '" + request.name + "' and new parent name '" + request.parent + "'"

        response = CopyFrameResponse()
        response.error_code = 0

        if request.name == "":
            print " Error: No name given"
            response.error_code = 1

        elif request.source_name == "":
            print " Error: No source name given"
            response.error_code = 3

        else:
            ## If not existing yet: create frame
            if request.name not in self.editor.frames:
                if request.source_name in self.editor.frames:
                    frame = copy.deepcopy(self.editor.frames[request.source_name])
                    frame.name = request.name
                else:
                    frame = Frame(request.name, parent=request.source_name)
                self.editor.command(Command_AddElement(self.editor, frame))
            else:
                ## Align with source frame
                frame = self.editor.frames[request.name]
                frame_tf = frame.tf_buffer.can_transform(request.name, request.source_name, rospy.Time.now(), rospy.Duration(1.0), rospy.Duration(0.01))
                if not frame_tf:
                    print " Error: tf can not transform. (Align)"
                    response.error_code = 4
                self.editor.command(Command_AlignElement(self.editor, frame, request.source_name, ['x', 'y', 'z', 'a', 'b', 'c']))

            ## Set parent
            if (request.parent != "") and (frame.parent != request.parent):
                ## Make sure the listener knows the new frame / its new aligned position
                self.editor.broadcast() # apparently you can't broadcast often enough
                frame_tf = frame.tf_buffer.can_transform(frame.parent, frame.name, rospy.Time.now(), rospy.Duration(1.0), rospy.Duration(0.01))
                new_tf = frame.tf_buffer.can_transform(request.parent, frame.name, rospy.Time.now(), rospy.Duration(1.0), rospy.Duration(0.01))
                if not (frame_tf and new_tf):
                    print " Error: tf can not transform."
                    response.error_code = 4
                self.editor.command(Command_SetParent(self.editor, frame, request.parent, True))

        return response

# eof
