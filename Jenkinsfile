node {
  def myRepo = checkout scm
  stage('Build Docker image') {
    git 'https://github.com/dfci/cidc-cli.git'
    docker.image('python:3.5.1').inside {
        stage('Print Python Version') {
            sh 'python --version'
        }
    }
  }
}
