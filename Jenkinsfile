pipeline {
    agent { docker { image 'python:3' }}
    stages {
        stage('build' {
            steps {
                sh 'pip install pipenv'
                sh 'pipenv install --system'
                sh 'bash cli.sh'
            }
        }
    }
}
