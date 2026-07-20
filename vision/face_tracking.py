class FaceTracker:

    def get_primary_face(self, faces):

        if len(faces) == 0:
            return None

        # Choose the largest face
        return max(faces, key=lambda f: f[2] * f[3])

    def get_face_center(self, face):

        x, y, w, h = face

        cx = x + w // 2
        cy = y + h // 2

        return cx, cy
