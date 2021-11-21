
class CustomAuthenticationForm(AuthenticationForm):

    class Meta:
        form = AuthenticationForm
        fields = "__all__"
        labels = {
            'username': 'Identifiant',
            'password1': 'Mot de Passe',
        }