import os
import unittest

# Define isolamento do banco para execução de testes de regressão
TEST_DB_PATH = os.path.abspath('test_regression.db')
os.environ['DATABASE_URL'] = f'sqlite:///{TEST_DB_PATH}'
os.environ['SECRET_KEY'] = 'test-secret-key'

from app import app, db, User


class UserCRUDRegressionTestCase(unittest.TestCase):
    """
    Casos de teste de regressão automatizados para a aplicação Flask CRUD.
    Garante a integridade e o funcionamento de todas as operações CRUD fundamentais
    no cenário pós-rollback utilizando SQLite local.
    """

    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        with app.app_context():
            db.create_all()

    @classmethod
    def tearDownClass(cls):
        with app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except OSError:
                pass

    def setUp(self):
        self.client = app.test_client()
        with app.app_context():
            # Limpa tabela antes de cada teste
            User.query.delete()
            db.session.commit()

    def tearDown(self):
        with app.app_context():
            db.session.rollback()

    def test_01_index_empty(self):
        """Verifica se a página inicial responde com HTTP 200 quando não há usuários."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_02_add_user_success(self):
        """Testa a criação de um usuário via POST /add e o redirecionamento."""
        payload = {
            'name': 'Ana Silva',
            'city': 'São Paulo',
            'contact': '11999998888'
        }
        response = self.client.post('/add', data=payload, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Ana Silva'.encode('utf-8'), response.data)
        self.assertIn('São Paulo'.encode('utf-8'), response.data)

        # Validação direta na camada de persistência
        with app.app_context():
            user = User.query.filter_by(name='Ana Silva').first()
            self.assertIsNotNone(user)
            self.assertEqual(user.city, 'São Paulo')
            self.assertEqual(user.contact, '11999998888')

    def test_03_edit_user_view(self):
        """Testa se a rota GET /edit/<id> carrega os dados existentes no formulário."""
        with app.app_context():
            user = User(name='Bruno Costa', city='Curitiba', contact='41988887777')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

        response = self.client.get(f'/edit/{user_id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Bruno Costa'.encode('utf-8'), response.data)
        self.assertIn('Curitiba'.encode('utf-8'), response.data)

    def test_04_edit_user_post_success(self):
        """Testa a atualização de um usuário existente via POST /edit/<id>."""
        with app.app_context():
            user = User(name='Carlos Souza', city='Belo Horizonte', contact='31977776666')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

        payload = {
            'name': 'Carlos Eduardo Souza',
            'city': 'Contagem',
            'contact': '31900001111'
        }
        response = self.client.post(f'/edit/{user_id}', data=payload, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Carlos Eduardo Souza'.encode('utf-8'), response.data)
        self.assertIn('Contagem'.encode('utf-8'), response.data)

        with app.app_context():
            updated = db.session.get(User, user_id)
            self.assertEqual(updated.name, 'Carlos Eduardo Souza')
            self.assertEqual(updated.city, 'Contagem')

    def test_05_delete_user_success(self):
        """Testa a exclusão de um usuário via GET /delete/<id>."""
        with app.app_context():
            user = User(name='Daniela Lima', city='Porto Alegre', contact='51966665555')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

        response = self.client.get(f'/delete/{user_id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Daniela Lima'.encode('utf-8'), response.data)

        with app.app_context():
            deleted = db.session.get(User, user_id)
            self.assertIsNone(deleted)

    def test_06_multiple_users_persistence(self):
        """Testa a inserção e persistência de múltiplos usuários na listagem."""
        users_data = [
            {'name': 'Usuario 1', 'city': 'Rio de Janeiro', 'contact': '21911112222'},
            {'name': 'Usuario 2', 'city': 'Salvador', 'contact': '71922223333'},
            {'name': 'Usuario 3', 'city': 'Fortaleza', 'contact': '85933334444'}
        ]
        for data in users_data:
            res = self.client.post('/add', data=data, follow_redirects=True)
            self.assertEqual(res.status_code, 200)

        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        for data in users_data:
            self.assertIn(data['name'].encode('utf-8'), response.data)

        with app.app_context():
            count = User.query.count()
            self.assertEqual(count, 3)

    def test_07_full_regression_crud_cycle(self):
        """
        Teste de regressão de ciclo completo (Create -> Read -> Update -> Delete).
        Simula o fluxo completo de operações para atestar a estabilidade pós-rollback.
        """
        # 1. Criação
        res_create = self.client.post('/add', data={
            'name': 'Regressao Teste',
            'city': 'Brasilia',
            'contact': '61999990000'
        }, follow_redirects=True)
        self.assertEqual(res_create.status_code, 200)

        with app.app_context():
            user = User.query.filter_by(name='Regressao Teste').first()
            self.assertIsNotNone(user)
            uid = user.id

        # 2. Leitura
        res_read = self.client.get('/')
        self.assertEqual(res_read.status_code, 200)
        self.assertIn('Regressao Teste'.encode('utf-8'), res_read.data)

        # 3. Atualização
        res_update = self.client.post(f'/edit/{uid}', data={
            'name': 'Regressao Modificado',
            'city': 'Goiania',
            'contact': '62988880000'
        }, follow_redirects=True)
        self.assertEqual(res_update.status_code, 200)
        self.assertIn('Regressao Modificado'.encode('utf-8'), res_update.data)

        # 4. Exclusão
        res_delete = self.client.get(f'/delete/{uid}', follow_redirects=True)
        self.assertEqual(res_delete.status_code, 200)
        self.assertNotIn('Regressao Modificado'.encode('utf-8'), res_delete.data)

        with app.app_context():
            self.assertIsNone(db.session.get(User, uid))


if __name__ == '__main__':
    unittest.main(verbosity=2)
